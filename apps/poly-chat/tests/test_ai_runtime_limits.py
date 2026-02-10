"""Tests for AI runtime limit propagation."""

from unittest.mock import MagicMock, patch

import pytest

from poly_chat.ai_runtime import send_message_to_ai


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

