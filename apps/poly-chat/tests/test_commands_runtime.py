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
async def test_model_unknown_name_keeps_provider_and_does_not_crash(command_handler, mock_session_manager):
    mock_session_manager.current_ai = "claude"

    result = await command_handler.set_model("foo-new-model")

    assert result == "Set model to foo-new-model (provider: claude)"
    assert mock_session_manager.current_model == "foo-new-model"
    assert mock_session_manager.current_ai == "claude"


@pytest.mark.asyncio
async def test_helper_unknown_name_keeps_provider_and_does_not_crash(command_handler, mock_session_manager):
    mock_session_manager.helper_ai = "openai"

    result = await command_handler.set_helper("foo-helper-model")

    assert result == "Helper model set to foo-helper-model (provider: openai)"
    assert mock_session_manager.helper_model == "foo-helper-model"
    assert mock_session_manager.helper_ai == "openai"


@pytest.mark.asyncio
async def test_model_switch_reconciles_incompatible_modes(command_handler, mock_session_manager):
    mock_session_manager.search_mode = True
    mock_session_manager.thinking_mode = True

    result = await command_handler.set_model("mistral-large-latest")

    assert result.startswith("Switched to mistral (mistral-large-latest)")
    assert "Search mode auto-disabled" in result
    assert "Thinking mode auto-disabled" in result
    assert mock_session_manager.search_mode is False
    assert mock_session_manager.thinking_mode is False


@pytest.mark.asyncio
async def test_model_switch_preserves_supported_mode(command_handler, mock_session_manager):
    mock_session_manager.search_mode = True
    mock_session_manager.thinking_mode = True

    result = await command_handler.set_model("gpt-5-mini")

    assert result.startswith("Switched to openai (gpt-5-mini)")
    assert "Thinking mode auto-disabled" in result
    assert mock_session_manager.search_mode is True
    assert mock_session_manager.thinking_mode is False
