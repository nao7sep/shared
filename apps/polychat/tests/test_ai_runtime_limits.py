"""Tests for AI runtime limit propagation."""

from unittest.mock import MagicMock, patch

import pytest

from polychat.ai.runtime import send_message_to_ai, validate_and_get_provider
from polychat.domain.chat import ChatDocument
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
            messages=[{"role": "user", "content": "hi"}],
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
            messages=[{"role": "user", "content": "hi"}],
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
            messages=[{"role": "user", "content": "hi"}],
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
