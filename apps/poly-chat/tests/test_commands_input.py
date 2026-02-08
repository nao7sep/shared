"""Tests for /input command behavior."""

import pytest
from poly_chat.commands import CommandHandler


@pytest.fixture
def mock_session():
    return {
        "current_ai": "claude",
        "current_model": "claude-haiku-4-5",
        "helper_ai": "claude",
        "helper_model": "claude-haiku-4-5",
        "input_mode": "quick",
        "profile": {
            "default_ai": "claude",
            "input_mode": "compose",
            "models": {"claude": "claude-haiku-4-5"},
            "api_keys": {},
        },
        "chat": {"metadata": {}, "messages": []},
    }


@pytest.mark.asyncio
async def test_input_show_current_mode(mock_session):
    handler = CommandHandler(mock_session)
    result = await handler.set_input_mode("")
    assert "Input mode: quick" in result


@pytest.mark.asyncio
async def test_input_set_compose(mock_session):
    handler = CommandHandler(mock_session)
    result = await handler.set_input_mode("compose")
    assert mock_session["input_mode"] == "compose"
    assert "Input mode set to compose" in result


@pytest.mark.asyncio
async def test_input_set_quick(mock_session):
    mock_session["input_mode"] = "compose"
    handler = CommandHandler(mock_session)
    result = await handler.set_input_mode("quick")
    assert mock_session["input_mode"] == "quick"
    assert "Input mode set to quick" in result


@pytest.mark.asyncio
async def test_input_default_uses_profile_value(mock_session):
    mock_session["input_mode"] = "quick"
    handler = CommandHandler(mock_session)
    result = await handler.set_input_mode("default")
    assert mock_session["input_mode"] == "compose"
    assert "profile default: compose" in result


@pytest.mark.asyncio
async def test_input_default_invalid_profile_falls_back(mock_session):
    mock_session["profile"]["input_mode"] = "invalid"
    handler = CommandHandler(mock_session)
    result = await handler.set_input_mode("default")
    assert mock_session["input_mode"] == "quick"
    assert "profile default: quick" in result


@pytest.mark.asyncio
async def test_input_invalid_value_raises(mock_session):
    handler = CommandHandler(mock_session)
    with pytest.raises(ValueError, match="Invalid input mode"):
        await handler.set_input_mode("banana")
