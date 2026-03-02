"""Tests for helper AI invocation."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from polychat.ai.helper_runtime import invoke_helper_ai
from polychat.domain.chat import ChatMessage
from polychat.domain.profile import RuntimeProfile


@pytest.mark.asyncio
async def test_invoke_helper_ai_uses_get_full_response_and_session_cache():
    """Helper invocation should use non-streaming API and pass session for caching."""
    profile = RuntimeProfile(
        default_ai="claude",
        models={"claude": "claude-haiku-4-5"},
        chats_dir=".",
        logs_dir=".",
        api_keys={"claude": {"type": "direct", "value": "test-key"}},
        timeout=300,
    )
    provider = MagicMock()
    provider.get_full_response = AsyncMock(
        return_value=("  helper output  ", {"usage": {"total_tokens": 12}})
    )
    session = object()

    with patch("polychat.keys.loader.load_api_key", return_value="test-key") as mock_load_key:
        with patch("polychat.ai.runtime.get_provider_instance", return_value=provider) as mock_get_provider:
            with patch("polychat.logging.log_event") as mock_log_event:
                response = await invoke_helper_ai(
                    provider_name="claude", model="claude-haiku-4-5",
                    profile=profile,
                    messages=[ChatMessage.new_user("Generate title")],
                    system_prompt="Do task",
                    task="title_generation",
                    session=session,
                )

    assert response == "helper output"
    mock_load_key.assert_called_once_with("claude", profile.api_keys["claude"])
    mock_get_provider.assert_called_once_with("claude", "test-key", session=session)
    call_kwargs = provider.get_full_response.await_args.kwargs
    assert len(call_kwargs["messages"]) == 1
    assert call_kwargs["messages"][0].role == "user"
    assert call_kwargs["messages"][0].content == ["Generate title"]
    assert call_kwargs["model"] == "claude-haiku-4-5"
    assert call_kwargs["system_prompt"] == "Do task"
    assert call_kwargs["max_output_tokens"] == 4096
    event_names = [call.args[0] for call in mock_log_event.call_args_list]
    assert "helper_ai_request" in event_names
    assert "helper_ai_response" in event_names


@pytest.mark.asyncio
async def test_invoke_helper_ai_missing_api_key_raises_value_error():
    """Missing helper API key should fail with clear ValueError."""
    profile = RuntimeProfile(
        default_ai="claude",
        models={"claude": "claude-haiku-4-5"},
        chats_dir=".",
        logs_dir=".",
        api_keys={},
        timeout=300,
    )

    with patch("polychat.logging.log_event"):
        with pytest.raises(ValueError, match="No API key configured for helper AI: claude"):
            await invoke_helper_ai(
                provider_name="claude", model="claude-haiku-4-5",
                profile=profile,
                messages=[ChatMessage.new_user("test")],
            )


@pytest.mark.asyncio
async def test_invoke_helper_ai_applies_helper_limits_when_configured():
    profile = RuntimeProfile(
        default_ai="claude",
        models={"claude": "claude-haiku-4-5"},
        chats_dir=".",
        logs_dir=".",
        api_keys={"claude": {"type": "direct", "value": "test-key"}},
        timeout=300,
        ai_limits={
            "helper": {
                "max_output_tokens": 123,
            }
        },
    )
    provider = MagicMock()
    provider.get_full_response = AsyncMock(return_value=("ok", {"usage": {}}))

    with patch("polychat.keys.loader.load_api_key", return_value="test-key"):
        with patch("polychat.ai.runtime.get_provider_instance", return_value=provider):
            with patch("polychat.logging.log_event"):
                await invoke_helper_ai(
                    provider_name="claude", model="claude-haiku-4-5",
                    profile=profile,
                    messages=[ChatMessage.new_user("Generate title")],
                )

    call_kwargs = provider.get_full_response.await_args.kwargs
    assert len(call_kwargs["messages"]) == 1
    assert call_kwargs["messages"][0].role == "user"
    assert call_kwargs["messages"][0].content == ["Generate title"]
    assert call_kwargs["model"] == "claude-haiku-4-5"
    assert call_kwargs["system_prompt"] is None
    assert call_kwargs["max_output_tokens"] == 123


@pytest.mark.asyncio
async def test_invoke_helper_ai_sanitizes_key_load_failure():
    profile = RuntimeProfile(
        default_ai="claude",
        models={"claude": "claude-haiku-4-5"},
        chats_dir=".",
        logs_dir=".",
        api_keys={"claude": {"type": "direct", "value": "test-key"}},
        timeout=300,
    )

    with (
        patch(
            "polychat.keys.loader.load_api_key",
            side_effect=RuntimeError("bad key sk-1234567890abcdefghijk"),
        ),
        patch("polychat.logging.log_event") as mock_log_event,
        patch("polychat.ai.helper_runtime.logging.error") as mock_logging_error,
        pytest.raises(
            ValueError,
            match="Error loading helper AI API key: bad key \\[REDACTED_API_KEY\\]",
        ),
    ):
        await invoke_helper_ai(
            provider_name="claude", model="claude-haiku-4-5",
            profile=profile,
            messages=[ChatMessage.new_user("test")],
        )

    assert mock_log_event.call_args.kwargs["error"] == "bad key [REDACTED_API_KEY]"
    assert mock_logging_error.call_args.args == (
        "Helper AI API key loading failed (provider=%s, model=%s): %s",
        "claude",
        "claude-haiku-4-5",
        "bad key [REDACTED_API_KEY]",
    )
    assert mock_logging_error.call_args.kwargs == {}


@pytest.mark.asyncio
async def test_invoke_helper_ai_sanitizes_provider_failure():
    profile = RuntimeProfile(
        default_ai="claude",
        models={"claude": "claude-haiku-4-5"},
        chats_dir=".",
        logs_dir=".",
        api_keys={"claude": {"type": "direct", "value": "test-key"}},
        timeout=300,
    )
    provider = MagicMock()
    provider.get_full_response = AsyncMock(
        side_effect=RuntimeError("provider failed sk-1234567890abcdefghijk")
    )

    with (
        patch("polychat.keys.loader.load_api_key", return_value="test-key"),
        patch("polychat.ai.runtime.get_provider_instance", return_value=provider),
        patch("polychat.logging.log_event") as mock_log_event,
        patch("polychat.ai.helper_runtime.logging.error") as mock_logging_error,
        pytest.raises(
            ValueError,
            match="Error invoking helper AI: provider failed \\[REDACTED_API_KEY\\]",
        ),
    ):
        await invoke_helper_ai(
            provider_name="claude", model="claude-haiku-4-5",
            profile=profile,
            messages=[ChatMessage.new_user("Generate title")],
        )

    assert mock_log_event.call_args.kwargs["error"] == "provider failed [REDACTED_API_KEY]"
    assert mock_logging_error.call_args.args == (
        "Error invoking helper AI (provider=%s, model=%s): %s",
        "claude",
        "claude-haiku-4-5",
        "provider failed [REDACTED_API_KEY]",
    )
    assert mock_logging_error.call_args.kwargs == {}
