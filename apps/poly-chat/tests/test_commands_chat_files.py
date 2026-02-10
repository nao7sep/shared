"""Tests for chat-file command UX behavior."""

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
async def test_new_chat_no_open_prompts_and_opens_on_default_yes(mock_session_manager):
    mock_session_manager.chat_path = None
    interaction = _InteractionStub(prompt_text_result="")
    command_handler = CommandHandler(mock_session_manager, interaction=interaction)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "poly_chat.commands.chat_files.generate_chat_filename",
            lambda _chats_dir, _name: "/test/chats/new-chat.json",
        )
        result = await command_handler.new_chat("")

    assert interaction.prompt_text.await_count == 1
    assert result == CommandSignal(kind="new_chat", chat_path="/test/chats/new-chat.json")


@pytest.mark.asyncio
async def test_new_chat_no_open_can_create_without_switch(mock_session_manager):
    mock_session_manager.chat_path = None
    interaction = _InteractionStub(prompt_text_result="n")
    command_handler = CommandHandler(mock_session_manager, interaction=interaction)
    save_mock = AsyncMock()

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "poly_chat.commands.chat_files.generate_chat_filename",
            lambda _chats_dir, _name: "/test/chats/new-chat.json",
        )
        mp.setattr(
            "poly_chat.commands.chat_files.load_chat",
            lambda _path: {"metadata": {}, "messages": []},
        )
        mp.setattr("poly_chat.commands.chat_files.save_chat", save_mock)
        result = await command_handler.new_chat("")

    assert result == "Created new chat (not opened): /test/chats/new-chat.json"
    save_mock.assert_awaited_once_with(
        "/test/chats/new-chat.json",
        {"metadata": {}, "messages": []},
    )


@pytest.mark.asyncio
async def test_new_chat_with_open_chat_skips_prompt(mock_session_manager):
    mock_session_manager.chat_path = "/test/chats/current.json"
    interaction = _InteractionStub(prompt_text_result="n")
    command_handler = CommandHandler(mock_session_manager, interaction=interaction)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "poly_chat.commands.chat_files.generate_chat_filename",
            lambda _chats_dir, _name: "/test/chats/new-chat.json",
        )
        result = await command_handler.new_chat("")

    interaction.prompt_text.assert_not_called()
    assert result == CommandSignal(kind="new_chat", chat_path="/test/chats/new-chat.json")

