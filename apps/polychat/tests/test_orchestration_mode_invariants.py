"""Focused invariants for retry/secret/pending-error orchestration behavior."""

from __future__ import annotations

from copy import deepcopy
from unittest.mock import AsyncMock, patch

import pytest

from polychat.commands.types import CommandSignal
from polychat.orchestrator import ChatOrchestrator
from polychat.orchestrator_types import ContinueAction, PrintAction, SendAction
from polychat.session_manager import SessionManager


@pytest.fixture
def manager() -> SessionManager:
    return SessionManager(
        profile={
            "chats_dir": "/test/chats",
            "logs_dir": "/test/logs",
        },
        current_ai="claude",
        current_model="claude-haiku-4-5",
    )


@pytest.fixture
def orchestrator(manager: SessionManager) -> ChatOrchestrator:
    return ChatOrchestrator(manager)


def _chat_with_pending_error() -> dict:
    return {
        "metadata": {},
        "messages": [
            {"role": "user", "content": "hello"},
            {"role": "error", "content": "timeout"},
        ],
    }


@pytest.mark.asyncio
async def test_pending_error_allows_retry_mode_send(orchestrator: ChatOrchestrator) -> None:
    chat_data = _chat_with_pending_error()
    orchestrator.manager.switch_chat("/test/chat.json", chat_data)
    orchestrator.manager.enter_retry_mode([{"role": "user", "content": "hello"}], target_index=1)

    action = await orchestrator.handle_user_message(
        "retry question",
        "/test/chat.json",
        chat_data,
    )

    assert isinstance(action, SendAction)
    assert action.mode == "retry"
    assert action.retry_user_input == "retry question"


@pytest.mark.asyncio
async def test_pending_error_allows_secret_mode_send(orchestrator: ChatOrchestrator) -> None:
    chat_data = _chat_with_pending_error()
    orchestrator.manager.switch_chat("/test/chat.json", chat_data)
    orchestrator.manager.enter_secret_mode(chat_data["messages"])

    action = await orchestrator.handle_user_message(
        "secret question",
        "/test/chat.json",
        chat_data,
    )

    assert isinstance(action, SendAction)
    assert action.mode == "secret"


@pytest.mark.asyncio
async def test_apply_retry_invalid_target_keeps_retry_mode(orchestrator: ChatOrchestrator) -> None:
    chat_data = {
        "metadata": {},
        "messages": [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ],
    }
    orchestrator.manager.switch_chat("/test/chat.json", chat_data)
    orchestrator.manager.enter_retry_mode(
        [{"role": "user", "content": "hello"}],
        target_index=99,
    )
    retry_hex_id = orchestrator.manager.add_retry_attempt("retry q", "retry a")

    with patch.object(orchestrator.manager, "save_current_chat", new_callable=AsyncMock) as mock_save:
        action = await orchestrator.handle_command_response(
            CommandSignal(kind="apply_retry", value=retry_hex_id),
            current_chat_path="/test/chat.json",
            current_chat_data=chat_data,
        )

    assert isinstance(action, PrintAction)
    assert action.message == "Retry target is no longer valid"
    assert orchestrator.manager.retry_mode is True
    mock_save.assert_not_called()


@pytest.mark.asyncio
async def test_cancel_retry_clears_retry_state(orchestrator: ChatOrchestrator) -> None:
    orchestrator.manager.enter_retry_mode([{"role": "user", "content": "base"}], target_index=0)
    orchestrator.manager.add_retry_attempt("retry q", "retry a")

    action = await orchestrator.handle_command_response(
        CommandSignal(kind="cancel_retry"),
        current_chat_path=None,
        current_chat_data=None,
    )

    assert isinstance(action, PrintAction)
    assert action.message == "Cancelled retry mode"
    assert orchestrator.manager.retry_mode is False
    assert orchestrator.manager.get_latest_retry_attempt_id() is None
    with pytest.raises(ValueError, match="Not in retry mode"):
        orchestrator.manager.get_retry_context()


@pytest.mark.asyncio
async def test_secret_mode_ai_response_does_not_mutate_or_persist_chat(
    orchestrator: ChatOrchestrator,
) -> None:
    chat_data = {
        "metadata": {},
        "messages": [{"role": "user", "content": "persisted"}],
    }
    before = deepcopy(chat_data)
    reserved_hex_id = orchestrator.manager.reserve_hex_id()

    with patch.object(orchestrator.manager, "save_current_chat", new_callable=AsyncMock) as mock_save:
        action = await orchestrator.handle_ai_response(
            "secret response",
            chat_path="/test/chat.json",
            chat_data=chat_data,
            mode="secret",
            assistant_hex_id=reserved_hex_id,
        )

    assert isinstance(action, ContinueAction)
    assert chat_data == before
    assert reserved_hex_id not in orchestrator.manager.hex_id_set
    mock_save.assert_not_called()
