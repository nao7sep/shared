"""Tests for /input command behavior."""

import pytest


@pytest.mark.asyncio
async def test_input_show_current_mode(command_handler, mock_session_manager):
    result = await command_handler.set_input_mode("")
    assert "Input mode: quick" in result


@pytest.mark.asyncio
async def test_input_set_compose(command_handler, mock_session_manager):
    result = await command_handler.set_input_mode("compose")
    assert mock_session_manager.input_mode == "compose"
    assert "Input mode set to compose" in result


@pytest.mark.asyncio
async def test_input_set_quick(command_handler, mock_session_manager):
    mock_session_manager.input_mode = "compose"
    result = await command_handler.set_input_mode("quick")
    assert mock_session_manager.input_mode == "quick"
    assert "Input mode set to quick" in result


@pytest.mark.asyncio
async def test_input_default_uses_profile_value(command_handler, mock_session_manager):
    mock_session_manager.input_mode = "quick"
    mock_session_manager.profile["input_mode"] = "compose"
    result = await command_handler.set_input_mode("default")
    assert mock_session_manager.input_mode == "compose"
    assert "profile default: compose" in result


@pytest.mark.asyncio
async def test_input_default_invalid_profile_falls_back(command_handler, mock_session_manager):
    mock_session_manager.profile["input_mode"] = "invalid"
    result = await command_handler.set_input_mode("default")
    assert mock_session_manager.input_mode == "quick"
    assert "profile default: quick" in result


@pytest.mark.asyncio
async def test_input_invalid_value_raises(command_handler):
    with pytest.raises(ValueError, match="Invalid input mode"):
        await command_handler.set_input_mode("banana")
