"""Tests for /rewind command."""

import pytest
from poly_chat.commands import CommandHandler
from poly_chat.session_manager import SessionManager


class FakeInteraction:
    """Deterministic async interaction adapter for command tests."""

    def __init__(self, responses: list[str] | None = None):
        self.responses = list(responses or ["yes"])

    async def prompt_text(self, prompt: str) -> str:
        if self.responses:
            return self.responses.pop(0)
        return "yes"

    async def prompt_chat_selection(
        self,
        chats_dir: str,
        *,
        action: str = "open",
        allow_cancel: bool = True,
    ) -> str | None:
        return None


@pytest.fixture
def rewind_manager():
    chat_data = {
        "metadata": {},
        "messages": [
            {"role": "user", "content": ["Q1"], "hex_id": "a3f"},
            {"role": "assistant", "content": ["A1"], "model": "claude-haiku-4-5", "hex_id": "b2c"},
            {"role": "user", "content": ["Q2"], "hex_id": "c1d"},
        ],
    }
    manager = SessionManager(
        profile={
            "default_ai": "claude",
            "models": {"claude": "claude-haiku-4-5"},
            "input_mode": "quick",
            "api_keys": {},
            "chats_dir": "/test/chats",
            "logs_dir": "/test/logs",
            "timeout": 30,
        },
        current_ai="claude",
        current_model="claude-haiku-4-5",
        chat=chat_data,
        chat_path="/tmp/test-chat.json",
    )
    manager._state.hex_id_set = {"a3f", "b2c", "c1d"}
    return manager


@pytest.fixture
def rewind_handler(rewind_manager):
    return CommandHandler(rewind_manager, interaction=FakeInteraction(["yes"] * 20))


@pytest.mark.asyncio
async def test_rewind_accepts_hex_id_only(rewind_handler, rewind_manager):
    target_hex_id = rewind_manager.chat["messages"][1]["hex_id"]
    result = await rewind_handler.rewind_messages(target_hex_id)
    assert result == f"Deleted 2 message(s) from [{target_hex_id}] onwards"
    assert len(rewind_manager.chat["messages"]) == 1


@pytest.mark.asyncio
async def test_rewind_accepts_last(rewind_handler, rewind_manager):
    rewind_manager.chat["messages"] = [
        {"role": "user", "content": ["Q1"], "hex_id": "a3f"},
        {"role": "assistant", "content": ["A1"], "model": "claude-haiku-4-5", "hex_id": "b2c"},
        {"role": "user", "content": ["Q2"], "hex_id": "c1d"},
        {"role": "assistant", "content": ["A2"], "model": "claude-haiku-4-5", "hex_id": "d4e"},
    ]

    result = await rewind_handler.rewind_messages("last")
    assert result == "Deleted 2 message(s) from [c1d] onwards"
    assert len(rewind_manager.chat["messages"]) == 2


@pytest.mark.asyncio
async def test_rewind_no_args_defaults_to_last(rewind_handler, rewind_manager):
    rewind_manager.chat["messages"] = [
        {"role": "user", "content": ["Q1"], "hex_id": "a3f"},
        {"role": "assistant", "content": ["A1"], "model": "claude-haiku-4-5", "hex_id": "b2c"},
        {"role": "error", "content": ["timeout"], "hex_id": "c1d"},
    ]

    result = await rewind_handler.rewind_messages("")

    assert result == "Deleted 1 message(s) from [c1d] onwards"
    assert len(rewind_manager.chat["messages"]) == 2


@pytest.mark.asyncio
async def test_rewind_rejects_integer_target(rewind_handler):
    with pytest.raises(ValueError, match="Use a hex ID or 'last'"):
        await rewind_handler.rewind_messages("1")


@pytest.mark.asyncio
async def test_rewind_last_deletes_last_user_assistant_pair(rewind_handler, rewind_manager):
    rewind_manager.chat["messages"] = [
        {"role": "user", "content": ["Q1"], "hex_id": "a3f"},
        {"role": "assistant", "content": ["A1"], "model": "claude-haiku-4-5", "hex_id": "b2c"},
        {"role": "user", "content": ["Q2"], "hex_id": "c1d"},
        {"role": "assistant", "content": ["A2"], "model": "claude-haiku-4-5", "hex_id": "d4e"},
    ]

    result = await rewind_handler.rewind_messages("last")

    assert result == "Deleted 2 message(s) from [c1d] onwards"
    assert len(rewind_manager.chat["messages"]) == 2


@pytest.mark.asyncio
async def test_rewind_last_deletes_last_user_error_pair(rewind_handler, rewind_manager):
    rewind_manager.chat["messages"] = [
        {"role": "user", "content": ["Q1"], "hex_id": "a3f"},
        {"role": "assistant", "content": ["A1"], "model": "claude-haiku-4-5", "hex_id": "b2c"},
        {"role": "user", "content": ["Q2"], "hex_id": "c1d"},
        {"role": "error", "content": ["timeout"], "hex_id": "d4e"},
    ]

    result = await rewind_handler.rewind_messages("last")

    assert result == "Deleted 2 message(s) from [c1d] onwards"
    assert len(rewind_manager.chat["messages"]) == 2


@pytest.mark.asyncio
async def test_rewind_last_deletes_trailing_error_after_good_pair(rewind_handler, rewind_manager):
    rewind_manager.chat["messages"] = [
        {"role": "user", "content": ["good user"], "hex_id": "a3f"},
        {"role": "assistant", "content": ["good answer"], "model": "claude-haiku-4-5", "hex_id": "b2c"},
        {"role": "error", "content": ["timeout"], "hex_id": "c1d"},
    ]

    result = await rewind_handler.rewind_messages("last")

    assert result == "Deleted 1 message(s) from [c1d] onwards"
    assert len(rewind_manager.chat["messages"]) == 2


@pytest.mark.asyncio
async def test_rewind_last_rejects_incomplete_tail(rewind_handler, rewind_manager):
    rewind_manager.chat["messages"] = [
        {"role": "user", "content": ["Q1"], "hex_id": "a3f"},
        {"role": "assistant", "content": ["A1"], "model": "claude-haiku-4-5", "hex_id": "b2c"},
        {"role": "user", "content": ["Q2"], "hex_id": "c1d"},
    ]

    with pytest.raises(ValueError, match="complete user\\+assistant or user\\+error turn"):
        await rewind_handler.rewind_messages("last")


@pytest.mark.asyncio
async def test_rewind_turn_keyword_removed(rewind_handler):
    with pytest.raises(ValueError, match="Use a hex ID or 'last'"):
        await rewind_handler.rewind_messages("turn")


@pytest.mark.asyncio
async def test_rewind_cancelled_on_non_yes(rewind_handler, rewind_manager):
    rewind_handler.interaction = FakeInteraction(["no"])
    rewind_manager.chat["messages"] = [
        {"role": "user", "content": ["Q1"], "hex_id": "a3f"},
        {"role": "assistant", "content": ["A1"], "model": "claude-haiku-4-5", "hex_id": "b2c"},
        {"role": "user", "content": ["Q2"], "hex_id": "c1d"},
        {"role": "assistant", "content": ["A2"], "model": "claude-haiku-4-5", "hex_id": "d4e"},
    ]
    initial_len = len(rewind_manager.chat["messages"])

    result = await rewind_handler.rewind_messages("last")

    assert result == "Rewind cancelled"
    assert len(rewind_manager.chat["messages"]) == initial_len
