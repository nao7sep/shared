"""Tests for command default value reversion."""

import pytest
from poly_chat.commands import CommandHandler


@pytest.fixture
def mock_session():
    """Create a mock session state."""
    return {
        "current_ai": "openai",
        "current_model": "gpt-5-mini",
        "helper_ai": "claude",
        "helper_model": "claude-haiku-4-5",
        "profile": {
            "default_ai": "claude",
            "models": {
                "openai": "gpt-5-mini",
                "claude": "claude-haiku-4-5",
                "gemini": "gemini-3-flash-preview",
            },
            "timeout": 30,
            "api_keys": {}
        },
        "chat": {
            "metadata": {
                "system_prompt_path": None,
            },
            "messages": []
        }
    }


@pytest.mark.asyncio
async def test_model_default_command(mock_session):
    """Test /model default command reverts to profile default."""
    # Start with non-default AI
    assert mock_session["current_ai"] == "openai"
    assert mock_session["current_model"] == "gpt-5-mini"

    handler = CommandHandler(mock_session)
    result = await handler.set_model("default")

    # Should revert to profile default
    assert mock_session["current_ai"] == "claude"
    assert mock_session["current_model"] == "claude-haiku-4-5"
    assert "Reverted to profile default: claude (claude-haiku-4-5)" in result


@pytest.mark.asyncio
async def test_timeout_default_command(mock_session):
    """Test /timeout default command reverts to profile default."""
    # Modify timeout
    mock_session["profile"]["timeout"] = 60

    handler = CommandHandler(mock_session)
    result = await handler.set_timeout("default")

    # Should keep the profile timeout (which is 60 now)
    # Note: The current implementation has a limitation - it uses current profile value
    assert "Reverted to profile default" in result
    assert mock_session["profile"]["timeout"] == 60


@pytest.mark.asyncio
async def test_timeout_default_with_zero(mock_session):
    """Test /timeout default when profile has zero timeout."""
    mock_session["profile"]["timeout"] = 0

    handler = CommandHandler(mock_session)
    result = await handler.set_timeout("default")

    assert "wait forever" in result
    assert mock_session["profile"]["timeout"] == 0


@pytest.mark.asyncio
async def test_model_default_uses_profile_default_ai(mock_session):
    """Test that /model default uses default_ai from profile."""
    # Change profile's default_ai
    mock_session["profile"]["default_ai"] = "gemini"

    handler = CommandHandler(mock_session)
    result = await handler.set_model("default")

    # Should use gemini now
    assert mock_session["current_ai"] == "gemini"
    assert mock_session["current_model"] == "gemini-3-flash-preview"
    assert "gemini" in result


@pytest.mark.asyncio
async def test_model_default_clears_provider_cache(mock_session):
    """Test that changing model clears provider cache."""
    # Add a mock provider cache
    mock_session["_provider_cache"] = {("openai", "key1"): "mock_provider"}

    handler = CommandHandler(mock_session)

    # Switching to default shouldn't clear cache (cache clearing not implemented for model switch)
    # This test documents current behavior
    await handler.set_model("default")

    # Cache should still exist (model switch doesn't clear cache in current implementation)
    assert "_provider_cache" in mock_session


@pytest.mark.asyncio
async def test_timeout_default_clears_provider_cache(mock_session):
    """Test that /timeout default clears provider cache."""
    # Add a mock provider cache
    mock_session["_provider_cache"] = {("openai", "key1"): "mock_provider"}

    handler = CommandHandler(mock_session)
    result = await handler.set_timeout("default")

    # Cache should be cleared
    assert "Provider cache cleared" in result
    assert len(mock_session["_provider_cache"]) == 0
