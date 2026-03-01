"""Tests for AI runtime limit propagation and runtime error handling."""

from unittest.mock import MagicMock, patch

import pytest

from polychat.ai.runtime import send_message_to_ai, validate_and_get_provider
from polychat.domain.chat import ChatDocument, ChatMessage
from polychat.domain.profile import RuntimeProfile
from polychat.session.state import SessionState
from test_helpers import make_profile


async def _empty_stream():
    if False:
        yield ""


@pytest.mark.asyncio
async def test_send_message_to_ai_omits_limit_kwargs_when_unset():
    provider = MagicMock()
    provider.send_message = MagicMock(return_value=_empty_stream())

    with patch("polychat.ai.runtime.log_event"):
        await send_message_to_ai(
            provider_instance=provider,
            messages=[ChatMessage.new_user("hi")],
            model="gpt-5-mini",
            provider_name="openai",
            profile=make_profile(),
            search=False,
        )

    kwargs = provider.send_message.call_args.kwargs
    assert "max_output_tokens" not in kwargs


@pytest.mark.asyncio
async def test_send_message_to_ai_applies_profile_limits():
    provider = MagicMock()
    provider.send_message = MagicMock(return_value=_empty_stream())

    profile = make_profile(
        ai_limits={
            "default": {"max_output_tokens": 1000},
            "providers": {
                "claude": {
                    "search_max_output_tokens": 2000,
                }
            },
        }
    )

    with patch("polychat.ai.runtime.log_event"):
        await send_message_to_ai(
            provider_instance=provider,
            messages=[ChatMessage.new_user("hi")],
            model="claude-haiku-4-5",
            provider_name="claude",
            profile=profile,
            search=True,
        )

    kwargs = provider.send_message.call_args.kwargs
    assert kwargs["max_output_tokens"] == 2000


@pytest.mark.asyncio
async def test_send_message_to_ai_applies_claude_fallback_limit_when_unset():
    provider = MagicMock()
    provider.send_message = MagicMock(return_value=_empty_stream())

    with patch("polychat.ai.runtime.log_event"):
        await send_message_to_ai(
            provider_instance=provider,
            messages=[ChatMessage.new_user("hi")],
            model="claude-haiku-4-5",
            provider_name="claude",
            profile=make_profile(),
            search=False,
        )

    kwargs = provider.send_message.call_args.kwargs
    assert kwargs["max_output_tokens"] == 4096


def _build_session(
    timeout: int | float = 300,
    *,
    provider: str = "openai",
    model: str = "gpt-5-mini",
    ai_limits: dict | None = None,
) -> SessionState:
    profile = RuntimeProfile(
        default_ai=provider,
        models={provider: model},
        chats_dir=".",
        logs_dir=".",
        api_keys={provider: {"type": "direct", "value": "test-key"}},
        timeout=timeout,
        ai_limits=ai_limits,
    )

    return SessionState(
        current_ai=provider,
        current_model=model,
        helper_ai=provider,
        helper_model=model,
        profile=profile,
        chat=ChatDocument.empty(),
    )


@pytest.mark.parametrize(
    ("provider_name", "search", "expected_timeout"),
    [
        ("openai", False, 300),
        ("openai", True, 900),
        ("claude", False, 300),
        ("claude", True, 900),
    ],
)
def test_validate_and_get_provider_applies_mode_timeout_multiplier(
    provider_name: str,
    search: bool,
    expected_timeout: int,
):
    model = "claude-haiku-4-5" if provider_name == "claude" else "gpt-5-mini"
    session = _build_session(
        timeout=300,
        provider=provider_name,
        model=model,
    )
    captured: dict[str, int | float] = {}

    def fake_get_provider_instance(
        provider_name: str,
        api_key: str,
        session: object = None,
        timeout_sec: int | float | None = None,
    ) -> object:
        if timeout_sec is not None:
            captured["timeout"] = timeout_sec
        return object()

    with patch("polychat.ai.runtime.load_api_key", return_value="test-key"):
        with patch("polychat.ai.runtime.validate_api_key", return_value=True):
            with patch(
                "polychat.ai.runtime.get_provider_instance",
                side_effect=fake_get_provider_instance,
            ):
                provider_instance, error = validate_and_get_provider(
                    session,
                    search=search,
                )

    assert provider_instance is not None
    assert error is None
    assert captured["timeout"] == expected_timeout


def test_validate_and_get_provider_keeps_zero_timeout_without_multiplier():
    session = _build_session(timeout=0)
    captured: dict[str, int | float] = {}

    def fake_get_provider_instance(
        provider_name: str,
        api_key: str,
        session: object = None,
        timeout_sec: int | float | None = None,
    ) -> object:
        if timeout_sec is not None:
            captured["timeout"] = timeout_sec
        return object()

    with patch("polychat.ai.runtime.load_api_key", return_value="test-key"):
        with patch("polychat.ai.runtime.validate_api_key", return_value=True):
            with patch(
                "polychat.ai.runtime.get_provider_instance",
                side_effect=fake_get_provider_instance,
            ):
                provider, error = validate_and_get_provider(
                    session,
                    search=True,
                )

    assert provider is not None
    assert error is None
    assert captured["timeout"] == 0


@pytest.mark.asyncio
async def test_send_message_to_ai_sanitizes_error_in_logs():
    provider = MagicMock()
    provider.send_message = MagicMock(
        side_effect=RuntimeError("request failed sk-1234567890abcdefghijk")
    )

    with (
        patch("polychat.ai.runtime.log_event") as mock_log_event,
        patch("polychat.ai.runtime.logging.error") as mock_logging_error,
        pytest.raises(RuntimeError, match="request failed sk-1234567890abcdefghijk"),
    ):
        await send_message_to_ai(
            provider_instance=provider,
            messages=[ChatMessage.new_user("hi")],
            model="gpt-5-mini",
            provider_name="openai",
            profile=make_profile(),
            search=False,
        )

    ai_error_call = mock_log_event.call_args_list[-1]
    assert ai_error_call.args[0] == "ai_error"
    assert ai_error_call.kwargs["error"] == "request failed [REDACTED_API_KEY]"
    assert mock_logging_error.call_args.args == (
        "Error sending message to AI (provider=%s, model=%s, mode=%s): %s",
        "openai",
        "gpt-5-mini",
        "normal",
        "request failed [REDACTED_API_KEY]",
    )
    assert mock_logging_error.call_args.kwargs == {}


def test_validate_and_get_provider_sanitizes_key_load_failure_logs_and_error():
    session = _build_session()

    with (
        patch(
            "polychat.ai.runtime.load_api_key",
            side_effect=RuntimeError("bad key sk-1234567890abcdefghijk"),
        ),
        patch("polychat.ai.runtime.log_event") as mock_log_event,
        patch("polychat.ai.runtime.logging.error") as mock_logging_error,
    ):
        provider, error = validate_and_get_provider(session)

    assert provider is None
    assert error == "Error loading API key: bad key [REDACTED_API_KEY]"
    assert mock_log_event.call_args.kwargs["phase"] == "key_load_failed"
    assert mock_log_event.call_args.kwargs["error"] == "bad key [REDACTED_API_KEY]"
    assert mock_logging_error.call_args.args == (
        "API key loading error: %s",
        "bad key [REDACTED_API_KEY]",
    )
    assert mock_logging_error.call_args.kwargs == {}


def test_validate_and_get_provider_sanitizes_provider_init_failure_logs_and_error():
    session = _build_session()

    with (
        patch("polychat.ai.runtime.load_api_key", return_value="test-key"),
        patch("polychat.ai.runtime.validate_api_key", return_value=True),
        patch(
            "polychat.ai.runtime.get_provider_instance",
            side_effect=RuntimeError("init failed sk-1234567890abcdefghijk"),
        ),
        patch("polychat.ai.runtime.log_event") as mock_log_event,
        patch("polychat.ai.runtime.logging.error") as mock_logging_error,
    ):
        provider, error = validate_and_get_provider(session)

    assert provider is None
    assert error == "Error initializing provider: init failed [REDACTED_API_KEY]"
    assert mock_log_event.call_args.kwargs["phase"] == "provider_init_failed"
    assert mock_log_event.call_args.kwargs["error"] == "init failed [REDACTED_API_KEY]"
    assert mock_logging_error.call_args.args == (
        "Provider initialization error: %s",
        "init failed [REDACTED_API_KEY]",
    )
    assert mock_logging_error.call_args.kwargs == {}
