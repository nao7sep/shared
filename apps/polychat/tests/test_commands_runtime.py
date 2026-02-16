"""Tests for runtime command UX behavior."""

from unittest.mock import AsyncMock

import pytest

from poly_chat.commands import CommandHandler
from poly_chat.commands.types import CommandSignal


class _InteractionStub:
    def __init__(self, prompt_text_result: str = ""):
        self.prompt_text_result = prompt_text_result
        self.prompt_text = AsyncMock(side_effect=self._prompt_text_impl)
        self.prompt_chat_selection = AsyncMock(return_value=None)

    async def _prompt_text_impl(self, _prompt: str) -> str:
        return self.prompt_text_result


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
async def test_system_persona_name_shortcut(command_handler, mock_session_manager, tmp_path):
    """Test that /system razor maps to @/prompts/system/razor.txt"""
    # Create a temporary razor.txt in the expected location
    from poly_chat import path_utils
    from pathlib import Path
    
    # Initialize system_prompt in metadata (normally done when chat is created)
    mock_session_manager.chat["metadata"]["system_prompt"] = None
    
    # Mock the app root to point to our tmp directory
    app_root = tmp_path / "app"
    prompts_dir = app_root / "prompts" / "system"
    prompts_dir.mkdir(parents=True)
    
    razor_file = prompts_dir / "razor.txt"
    razor_file.write_text("Test razor persona prompt")
    
    # Temporarily patch the app root - it should return a Path object
    original_get_app_root = path_utils.get_app_root
    path_utils.get_app_root = lambda: Path(str(app_root))
    
    try:
        result = await command_handler.set_system_prompt("razor")
        
        assert result == "System prompt set to: razor persona"
        assert mock_session_manager.system_prompt == "Test razor persona prompt"
        assert mock_session_manager.system_prompt_path == "@/prompts/system/razor.txt"
        assert mock_session_manager.chat["metadata"]["system_prompt"] == "@/prompts/system/razor.txt"
    finally:
        path_utils.get_app_root = original_get_app_root


@pytest.mark.asyncio
async def test_secret_off_when_already_off(command_handler, mock_session_manager):
    result = await command_handler.secret_mode_command("off")
    assert result == "Secret mode already off"
    assert mock_session_manager.secret_mode is False


@pytest.mark.asyncio
async def test_retry_mode_excludes_last_user_assistant_interaction(command_handler, mock_session_manager):
    mock_session_manager.chat["messages"] = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hello!"},
        {"role": "user", "content": "nice to meet you"},
        {"role": "assistant", "content": "nice to meet you too!"},
    ]

    result = await command_handler.retry_mode("")

    assert result == "Retry mode enabled"
    assert mock_session_manager.get_retry_context() == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hello!"},
    ]


@pytest.mark.asyncio
async def test_retry_mode_excludes_failed_user_message_after_error(command_handler, mock_session_manager):
    mock_session_manager.chat["messages"] = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hello!"},
        {"role": "user", "content": "this failed"},
        {"role": "error", "content": "timeout"},
    ]

    result = await command_handler.retry_mode("")

    assert result == "Retry mode enabled"
    assert mock_session_manager.get_retry_context() == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hello!"},
    ]


@pytest.mark.asyncio
async def test_apply_no_args_uses_latest_retry_attempt(command_handler, mock_session_manager):
    mock_session_manager.enter_retry_mode([{"role": "user", "content": "base"}], target_index=1)
    first_id = mock_session_manager.add_retry_attempt("q1", "a1")
    latest_id = mock_session_manager.add_retry_attempt("q2", "a2")

    result = await command_handler.apply_retry("")

    assert first_id != latest_id
    assert result == CommandSignal(kind="apply_retry", value=latest_id)


@pytest.mark.asyncio
async def test_apply_last_uses_latest_retry_attempt(command_handler, mock_session_manager):
    mock_session_manager.enter_retry_mode([{"role": "user", "content": "base"}], target_index=1)
    latest_id = mock_session_manager.add_retry_attempt("q2", "a2")

    result = await command_handler.apply_retry("last")

    assert result == CommandSignal(kind="apply_retry", value=latest_id)


@pytest.mark.asyncio
async def test_apply_no_args_requires_retry_attempts(command_handler, mock_session_manager):
    mock_session_manager.enter_retry_mode([{"role": "user", "content": "base"}], target_index=1)

    result = await command_handler.apply_retry("")

    assert result == "No retry attempts available yet"


@pytest.mark.asyncio
async def test_apply_last_requires_retry_attempts(command_handler, mock_session_manager):
    mock_session_manager.enter_retry_mode([{"role": "user", "content": "base"}], target_index=1)

    result = await command_handler.apply_retry("last")

    assert result == "No retry attempts available yet"


@pytest.mark.asyncio
async def test_apply_explicit_hex_id_still_supported(command_handler, mock_session_manager):
    mock_session_manager.enter_retry_mode([{"role": "user", "content": "base"}], target_index=1)
    retry_hex_id = mock_session_manager.add_retry_attempt("q", "a")

    result = await command_handler.apply_retry(retry_hex_id)

    assert result == CommandSignal(kind="apply_retry", value=retry_hex_id)


@pytest.mark.asyncio
async def test_secret_on_off_literal_gives_hint(command_handler):
    result = await command_handler.secret_mode_command("on/off")
    assert result == "Use /secret on or /secret off"


@pytest.mark.asyncio
async def test_thinking_command_removed(command_handler):
    with pytest.raises(ValueError, match="Unknown command: /thinking"):
        await command_handler.execute_command("/thinking")


@pytest.mark.asyncio
async def test_model_unknown_name_returns_no_match(command_handler, mock_session_manager):
    mock_session_manager.current_ai = "claude"
    mock_session_manager.current_model = "claude-haiku-4-5"

    result = await command_handler.set_model("foo-new-model")

    assert result == "No model matches 'foo-new-model'."
    assert mock_session_manager.current_model == "claude-haiku-4-5"
    assert mock_session_manager.current_ai == "claude"


@pytest.mark.asyncio
async def test_helper_unknown_name_returns_no_match(command_handler, mock_session_manager):
    mock_session_manager.helper_ai = "openai"
    mock_session_manager.helper_model = "gpt-5-mini"

    result = await command_handler.set_helper("foo-helper-model")

    assert result == "No model matches 'foo-helper-model'."
    assert mock_session_manager.helper_model == "gpt-5-mini"
    assert mock_session_manager.helper_ai == "openai"


@pytest.mark.asyncio
async def test_model_switch_reconciles_incompatible_modes(command_handler, mock_session_manager):
    mock_session_manager.search_mode = True

    result = await command_handler.set_model("mistral-large-latest")

    assert result.startswith("Switched to mistral (mistral-large-latest)")
    assert "Search mode auto-disabled" in result
    assert mock_session_manager.search_mode is False


@pytest.mark.asyncio
async def test_model_switch_preserves_supported_mode(command_handler, mock_session_manager):
    mock_session_manager.search_mode = True

    result = await command_handler.set_model("gpt-5-mini")

    assert result.startswith("Switched to openai (gpt-5-mini)")
    assert "Search mode auto-disabled" not in result
    assert mock_session_manager.search_mode is True


@pytest.mark.asyncio
async def test_model_partial_match_switches_model(command_handler, mock_session_manager):
    result = await command_handler.set_model("op4")

    assert result == "Switched to claude (claude-opus-4-6) [matched from 'op4']"
    assert mock_session_manager.current_ai == "claude"
    assert mock_session_manager.current_model == "claude-opus-4-6"


@pytest.mark.asyncio
async def test_model_ambiguous_match_prompts_for_selection(mock_session_manager):
    interaction = _InteractionStub(prompt_text_result="2")
    command_handler = CommandHandler(mock_session_manager, interaction=interaction)

    result = await command_handler.set_model("g5")

    assert interaction.prompt_text.await_count == 1
    assert result.startswith("Switched to openai")
    assert "[matched from 'g5']" in result


@pytest.mark.asyncio
async def test_model_ambiguous_match_cancelled(mock_session_manager):
    interaction = _InteractionStub(prompt_text_result="")
    command_handler = CommandHandler(mock_session_manager, interaction=interaction)

    result = await command_handler.set_model("g5")

    assert result == "Model selection cancelled."


@pytest.mark.asyncio
async def test_helper_provider_shortcut_sets_profile_model(command_handler, mock_session_manager):
    result = await command_handler.set_helper("gpt")

    assert result == "Helper AI set to openai (gpt-5-mini)"
    assert mock_session_manager.helper_ai == "openai"
    assert mock_session_manager.helper_model == "gpt-5-mini"


@pytest.mark.asyncio
async def test_helper_partial_match_switches_model(command_handler, mock_session_manager):
    result = await command_handler.set_helper("op4")

    assert result == "Helper AI set to claude (claude-opus-4-6) [matched from 'op4']"
    assert mock_session_manager.helper_ai == "claude"
    assert mock_session_manager.helper_model == "claude-opus-4-6"


@pytest.mark.asyncio
async def test_helper_ambiguous_match_prompts_for_selection(mock_session_manager):
    interaction = _InteractionStub(prompt_text_result="1")
    command_handler = CommandHandler(mock_session_manager, interaction=interaction)

    result = await command_handler.set_helper("g5")

    assert interaction.prompt_text.await_count == 1
    assert result.startswith("Helper AI set to")
    assert "[matched from 'g5']" in result
