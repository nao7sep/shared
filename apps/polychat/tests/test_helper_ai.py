"""Tests for helper AI invocation."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from poly_chat.helper_ai import invoke_helper_ai


@pytest.mark.asyncio
async def test_invoke_helper_ai_uses_get_full_response_and_session_cache():
    """Helper invocation should use non-streaming API and pass session for caching."""
    profile_data = {
        "api_keys": {
            "claude": {"type": "direct", "value": "test-key"},
        }
    }
    provider = MagicMock()
    provider.get_full_response = AsyncMock(
        return_value=("  helper output  ", {"usage": {"total_tokens": 12}})
    )
    session = object()

    with patch("poly_chat.keys.loader.load_api_key", return_value="test-key") as mock_load_key:
        with patch("poly_chat.ai_runtime.get_provider_instance", return_value=provider) as mock_get_provider:
            with patch("poly_chat.logging_utils.log_event") as mock_log_event:
                response = await invoke_helper_ai(
                    helper_ai="claude",
                    helper_model="claude-haiku-4-5",
                    profile=profile_data,
                    messages=[{"role": "user", "content": "Generate title"}],
                    system_prompt="Do task",
                    task="title_generation",
                    session=session,
                )

    assert response == "helper output"
    mock_load_key.assert_called_once_with("claude", profile_data["api_keys"]["claude"])
    mock_get_provider.assert_called_once_with("claude", "test-key", session=session)
    provider.get_full_response.assert_awaited_once_with(
        messages=[{"role": "user", "content": "Generate title"}],
        model="claude-haiku-4-5",
        system_prompt="Do task",
        max_output_tokens=4096,
    )
    event_names = [call.args[0] for call in mock_log_event.call_args_list]
    assert "helper_ai_request" in event_names
    assert "helper_ai_response" in event_names


@pytest.mark.asyncio
async def test_invoke_helper_ai_missing_api_key_raises_value_error():
    """Missing helper API key should fail with clear ValueError."""
    profile_data = {"api_keys": {}}

    with patch("poly_chat.logging_utils.log_event"):
        with pytest.raises(ValueError, match="No API key configured for helper AI: claude"):
            await invoke_helper_ai(
                helper_ai="claude",
                helper_model="claude-haiku-4-5",
                profile=profile_data,
                messages=[{"role": "user", "content": "test"}],
            )


@pytest.mark.asyncio
async def test_invoke_helper_ai_applies_helper_limits_when_configured():
    profile_data = {
        "api_keys": {
            "claude": {"type": "direct", "value": "test-key"},
        },
        "ai_limits": {
            "helper": {
                "max_output_tokens": 123,
            }
        },
    }
    provider = MagicMock()
    provider.get_full_response = AsyncMock(return_value=("ok", {"usage": {}}))

    with patch("poly_chat.keys.loader.load_api_key", return_value="test-key"):
        with patch("poly_chat.ai_runtime.get_provider_instance", return_value=provider):
            with patch("poly_chat.logging_utils.log_event"):
                await invoke_helper_ai(
                    helper_ai="claude",
                    helper_model="claude-haiku-4-5",
                    profile=profile_data,
                    messages=[{"role": "user", "content": "Generate title"}],
                )

    provider.get_full_response.assert_awaited_once_with(
        messages=[{"role": "user", "content": "Generate title"}],
        model="claude-haiku-4-5",
        system_prompt=None,
        max_output_tokens=123,
    )
