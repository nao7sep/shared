"""Tests for AI runtime limit propagation."""

from unittest.mock import MagicMock, patch

import pytest

from poly_chat.ai_runtime import send_message_to_ai, validate_and_get_provider
from poly_chat.app_state import SessionState


async def _empty_stream():
    if False:
        yield ""


@pytest.mark.asyncio
async def test_send_message_to_ai_omits_limit_kwargs_when_unset():
    provider = MagicMock()
    provider.send_message = MagicMock(return_value=_empty_stream())

    with patch("poly_chat.ai_runtime.log_event"):
        await send_message_to_ai(
            provider_instance=provider,
            messages=[{"role": "user", "content": "hi"}],
            model="gpt-5-mini",
            provider_name="openai",
            profile={},
            search=False,
            thinking=False,
        )

    kwargs = provider.send_message.call_args.kwargs
    assert "max_output_tokens" not in kwargs
    assert "thinking_budget_tokens" not in kwargs


@pytest.mark.asyncio
async def test_send_message_to_ai_applies_resolved_limits():
    provider = MagicMock()
    provider.send_message = MagicMock(return_value=_empty_stream())

    profile = {
        "ai_limits": {
            "default": {"max_output_tokens": 1000},
            "providers": {
                "claude": {
                    "search_max_output_tokens": 2000,
                    "thinking_budget_tokens": 3000,
                }
            },
        }
    }

    with patch("poly_chat.ai_runtime.log_event"):
        await send_message_to_ai(
            provider_instance=provider,
            messages=[{"role": "user", "content": "hi"}],
            model="claude-haiku-4-5",
            provider_name="claude",
            profile=profile,
            search=True,
            thinking=True,
        )

    kwargs = provider.send_message.call_args.kwargs
    assert kwargs["max_output_tokens"] == 2000
    assert kwargs["thinking_budget_tokens"] == 3000


def _build_session(timeout: int | float = 30) -> SessionState:
    return SessionState(
        current_ai="openai",
        current_model="gpt-5-mini",
        helper_ai="openai",
        helper_model="gpt-5-mini",
        profile={
            "timeout": timeout,
            "api_keys": {"openai": {"type": "direct", "value": "test-key"}},
        },
        chat={},
    )


@pytest.mark.parametrize(
    ("search", "thinking", "expected_timeout"),
    [
        (False, False, 30),
        (True, False, 90),
        (False, True, 90),
        (True, True, 90),
    ],
)
def test_validate_and_get_provider_applies_mode_timeout_multiplier(
    search: bool,
    thinking: bool,
    expected_timeout: int,
):
    session = _build_session(timeout=30)
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

    with patch("poly_chat.ai_runtime.load_api_key", return_value="test-key"):
        with patch("poly_chat.ai_runtime.validate_api_key", return_value=True):
            with patch(
                "poly_chat.ai_runtime.get_provider_instance",
                side_effect=fake_get_provider_instance,
            ):
                provider, error = validate_and_get_provider(
                    session,
                    search=search,
                    thinking=thinking,
                )

    assert provider is not None
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

    with patch("poly_chat.ai_runtime.load_api_key", return_value="test-key"):
        with patch("poly_chat.ai_runtime.validate_api_key", return_value=True):
            with patch(
                "poly_chat.ai_runtime.get_provider_instance",
                side_effect=fake_get_provider_instance,
            ):
                provider, error = validate_and_get_provider(
                    session,
                    search=True,
                    thinking=True,
                )

    assert provider is not None
    assert error is None
    assert captured["timeout"] == 0
