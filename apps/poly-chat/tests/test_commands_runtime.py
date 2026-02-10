"""Tests for runtime command UX behavior."""

import pytest


@pytest.mark.asyncio
async def test_secret_no_args_shows_state_off(command_handler, mock_session_manager):
    result = await command_handler.secret_mode_command("")
    assert result == "Secret mode: off"
    assert mock_session_manager.secret_mode is False


@pytest.mark.asyncio
async def test_secret_no_args_shows_state_on(command_handler, mock_session_manager):
    mock_session_manager.secret_mode = True
    result = await command_handler.secret_mode_command("")
    assert result == "Secret mode: on"
    assert mock_session_manager.secret_mode is True


@pytest.mark.asyncio
async def test_secret_on_off_still_work(command_handler, mock_session_manager):
    result_on = await command_handler.secret_mode_command("on")
    assert result_on == "Secret mode enabled"
    assert mock_session_manager.secret_mode is True

    result_off = await command_handler.secret_mode_command("off")
    assert result_off == "Secret mode disabled"
    assert mock_session_manager.secret_mode is False


@pytest.mark.asyncio
async def test_secret_on_when_already_on(command_handler, mock_session_manager):
    mock_session_manager.secret_mode = True
    result = await command_handler.secret_mode_command("on")
    assert result == "Secret mode already on"
    assert mock_session_manager.secret_mode is True


@pytest.mark.asyncio
async def test_system_show_prefers_chat_unmapped_path(command_handler, mock_session_manager):
    mock_session_manager.chat["metadata"]["system_prompt"] = "~/prompts/custom.txt"
    mock_session_manager.system_prompt_path = "/mapped/path/custom.txt"

    result = await command_handler.set_system_prompt("")

    assert result == "Current system prompt: ~/prompts/custom.txt"


@pytest.mark.asyncio
async def test_secret_off_when_already_off(command_handler, mock_session_manager):
    result = await command_handler.secret_mode_command("off")
    assert result == "Secret mode already off"
    assert mock_session_manager.secret_mode is False


@pytest.mark.asyncio
async def test_secret_on_off_literal_gives_hint(command_handler):
    result = await command_handler.secret_mode_command("on/off")
    assert result == "Use /secret on or /secret off"


@pytest.mark.asyncio
async def test_secret_message_payload_not_supported(command_handler):
    result = await command_handler.secret_mode_command("/search latest ai news")
    assert (
        result
        == "One-shot /secret is not supported. "
        "Use /secret on, send message, then /secret off."
    )


@pytest.mark.asyncio
async def test_search_message_payload_not_supported(command_handler):
    result = await command_handler.search_mode_command("/secret my password is 1234")
    assert (
        result
        == "One-shot /search is not supported. "
        "Use /search on, send message, then /search off."
    )


@pytest.mark.asyncio
async def test_secret_slash_prefixed_payload_not_supported(command_handler):
    result = await command_handler.secret_mode_command("/tmp/my-secret-file.txt")
    assert (
        result
        == "One-shot /secret is not supported. "
        "Use /secret on, send message, then /secret off."
    )


@pytest.mark.asyncio
async def test_search_slash_prefixed_payload_not_supported(command_handler):
    result = await command_handler.search_mode_command("/Users/me/docs/topic.txt")
    assert (
        result
        == "One-shot /search is not supported. "
        "Use /search on, send message, then /search off."
    )
