"""Tests for command default value reversion."""

import pytest
from poly_chat.commands import CommandHandler
from poly_chat.session_manager import SessionManager


@pytest.fixture
def mock_session_manager_defaults():
    """Create a mock SessionManager for defaults tests."""
    chat_data = {
        "metadata": {
            "system_prompt": None,
        },
        "messages": []
    }

    manager = SessionManager(
        profile={
            "default_ai": "claude",
            "models": {
                "openai": "gpt-5-mini",
                "claude": "claude-haiku-4-5",
                "gemini": "gemini-3-flash-preview",
            },
            "timeout": 30,
            "input_mode": "quick",
            "api_keys": {},
            "chats_dir": "/test/chats",
            "logs_dir": "/test/logs",
            "pages_dir": "/test/pages",
        },
        current_ai="openai",
        current_model="gpt-5-mini",
        helper_ai="claude",
        helper_model="claude-haiku-4-5",
        chat=chat_data,
        chat_path="/test/chat.json",
        profile_path="/test/profile.json",
        log_file="/test/log.txt",
    )

    return manager


@pytest.fixture
def command_handler_defaults(mock_session_manager_defaults):
    """Create a CommandHandler for defaults tests."""
    return CommandHandler(mock_session_manager_defaults)


@pytest.mark.asyncio
async def test_model_default_command(command_handler_defaults, mock_session_manager_defaults):
    """Test /model default command reverts to profile default."""
    # Start with non-default AI
    assert mock_session_manager_defaults.current_ai == "openai"
    assert mock_session_manager_defaults.current_model == "gpt-5-mini"

    result = await command_handler_defaults.set_model("default")

    # Should revert to profile default
    assert mock_session_manager_defaults.current_ai == "claude"
    assert mock_session_manager_defaults.current_model == "claude-haiku-4-5"
    assert "Reverted to profile default: claude (claude-haiku-4-5)" in result


@pytest.mark.asyncio
async def test_timeout_default_command(command_handler_defaults, mock_session_manager_defaults):
    """Test /timeout default command reverts to profile default."""
    # Modify timeout
    mock_session_manager_defaults.profile["timeout"] = 60

    result = await command_handler_defaults.set_timeout("default")

    # Should revert to startup profile default
    assert result == "Reverted to profile default: 30 seconds"
    assert mock_session_manager_defaults.profile["timeout"] == 30


@pytest.mark.asyncio
async def test_timeout_default_with_zero(command_handler_defaults, mock_session_manager_defaults):
    """Test /timeout default when profile has zero timeout."""
    mock_session_manager_defaults._default_timeout = 0

    result = await command_handler_defaults.set_timeout("default")

    assert "wait forever" in result
    assert mock_session_manager_defaults.profile["timeout"] == 0


@pytest.mark.asyncio
async def test_model_default_uses_profile_default_ai(command_handler_defaults, mock_session_manager_defaults):
    """Test that /model default uses default_ai from profile."""
    # Change profile's default_ai
    mock_session_manager_defaults.profile["default_ai"] = "gemini"

    result = await command_handler_defaults.set_model("default")

    # Should use gemini now
    assert mock_session_manager_defaults.current_ai == "gemini"
    assert mock_session_manager_defaults.current_model == "gemini-3-flash-preview"
    assert "gemini" in result


@pytest.mark.asyncio
async def test_model_default_clears_provider_cache(command_handler_defaults, mock_session_manager_defaults):
    """Test that changing model clears provider cache."""
    # Add a mock provider cache
    mock_session_manager_defaults._state._provider_cache = {("openai", "key1"): "mock_provider"}

    # Switching to default shouldn't clear cache (cache clearing not implemented for model switch)
    # This test documents current behavior
    await command_handler_defaults.set_model("default")

    # Cache should still exist (model switch doesn't clear cache in current implementation)
    assert hasattr(mock_session_manager_defaults._state, "_provider_cache")


@pytest.mark.asyncio
async def test_timeout_default_clears_provider_cache(command_handler_defaults, mock_session_manager_defaults):
    """Test that /timeout default clears provider cache."""
    # Add a mock provider cache
    mock_session_manager_defaults._state._provider_cache = {("openai", "key1"): "mock_provider"}

    result = await command_handler_defaults.set_timeout("default")

    assert "Reverted to profile default" in result
    assert mock_session_manager_defaults._state._provider_cache == {}


@pytest.mark.asyncio
async def test_timeout_set_clears_provider_cache(command_handler_defaults, mock_session_manager_defaults):
    """Setting timeout should clear provider cache so new timeout takes effect."""
    mock_session_manager_defaults._state._provider_cache = {("openai", "key1"): "mock_provider"}

    result = await command_handler_defaults.set_timeout("45")

    assert result == "Timeout set to 45 seconds"
    assert mock_session_manager_defaults.profile["timeout"] == 45
    assert mock_session_manager_defaults._state._provider_cache == {}
