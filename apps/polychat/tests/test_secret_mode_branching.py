"""Tests for secret-mode runtime branching semantics."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from polychat.domain.chat import ChatDocument
from polychat.orchestrator import ChatOrchestrator
from polychat.orchestration.types import ContinueAction, PrintAction, SendAction
from polychat.session_manager import SessionManager
from test_helpers import make_profile


@pytest.fixture
def manager() -> SessionManager:
    return SessionManager(
        profile=make_profile(
            chats_dir="/test/chats",
            logs_dir="/test/logs",
        ),
        current_ai="claude",
        current_model="claude-haiku-4-5",
    )


@pytest.fixture
def orchestrator(manager: SessionManager) -> ChatOrchestrator:
    return ChatOrchestrator(manager)


def _base_chat() -> ChatDocument:
    return ChatDocument.from_raw({
        "metadata": {},
        "messages": [
            {"role": "user", "content": ["u1"]},
            {"role": "assistant", "content": ["a1"], "model": "claude-haiku-4-5"},
        ],
    })


@pytest.mark.asyncio
async def test_secret_success_appends_runtime_transcript_only(
    orchestrator: ChatOrchestrator,
) -> None:
    chat_data = _base_chat()
    orchestrator.manager.switch_chat("/test/chat.json", chat_data)
    orchestrator.manager.secret.enter(list(chat_data.messages))

    with patch.object(orchestrator.manager, "save_current_chat", new_callable=AsyncMock) as mock_save:
        action = await orchestrator.handle_ai_response(
            "secret a2",
            "/test/chat.json",
            chat_data,
            "secret",
            user_input="secret u2",
        )

    assert isinstance(action, ContinueAction)
    assert [message.content for message in orchestrator.manager.secret.secret_messages] == [
        ["secret u2"],
        ["secret a2"],
    ]
    assert [message.content for message in chat_data.messages] == [["u1"], ["a1"]]
    mock_save.assert_not_called()


@pytest.mark.asyncio
async def test_secret_preflight_failure_records_standalone_secret_error(
    orchestrator: ChatOrchestrator,
) -> None:
    chat_data = _base_chat()
    orchestrator.manager.switch_chat("/test/chat.json", chat_data)
    orchestrator.manager.secret.enter(list(chat_data.messages))

    with patch.object(orchestrator.manager, "save_current_chat", new_callable=AsyncMock) as mock_save:
        handled = await orchestrator.rollback_pre_send_failure(
            chat_path="/test/chat.json",
            chat_data=chat_data,
            mode="secret",
            error_message="provider unavailable",
        )

    assert handled is False
    assert [message.role for message in orchestrator.manager.secret.secret_messages] == ["error"]
    assert orchestrator.manager.secret.secret_messages[0].content == ["provider unavailable"]
    assert [message.content for message in chat_data.messages] == [["u1"], ["a1"]]
    mock_save.assert_not_called()


@pytest.mark.asyncio
async def test_secret_request_failure_records_user_error_turn_only_in_secret_state(
    orchestrator: ChatOrchestrator,
) -> None:
    chat_data = _base_chat()
    orchestrator.manager.switch_chat("/test/chat.json", chat_data)
    orchestrator.manager.secret.enter(list(chat_data.messages))

    with patch.object(orchestrator.manager, "save_current_chat", new_callable=AsyncMock) as mock_save:
        action = await orchestrator.handle_ai_error(
            RuntimeError("network down"),
            "/test/chat.json",
            chat_data,
            "secret",
            user_input="secret u2",
        )

    assert isinstance(action, PrintAction)
    assert [message.role for message in orchestrator.manager.secret.secret_messages] == [
        "user",
        "error",
    ]
    assert [message.content for message in orchestrator.manager.secret.secret_messages] == [
        ["secret u2"],
        ["network down"],
    ]
    assert [message.content for message in chat_data.messages] == [["u1"], ["a1"]]
    mock_save.assert_not_called()


@pytest.mark.asyncio
async def test_secret_pending_error_blocks_further_secret_messages(
    orchestrator: ChatOrchestrator,
) -> None:
    chat_data = _base_chat()
    orchestrator.manager.switch_chat("/test/chat.json", chat_data)
    orchestrator.manager.secret.enter(list(chat_data.messages))
    orchestrator.manager.secret.append_error("timeout", user_msg="secret u2")

    action = await orchestrator.handle_user_message("secret u3")

    assert isinstance(action, PrintAction)
    assert "Secret mode cannot continue" in action.message


def test_secret_exit_clears_runtime_transcript(orchestrator: ChatOrchestrator) -> None:
    chat_data = _base_chat()
    orchestrator.manager.switch_chat("/test/chat.json", chat_data)
    orchestrator.manager.secret.enter(list(chat_data.messages))
    orchestrator.manager.secret.append_success(
        "secret u2",
        "secret a2",
        model="claude-haiku-4-5",
    )

    orchestrator.manager.secret.exit()

    assert orchestrator.manager.secret.active is False
    assert orchestrator.manager.secret.base_messages == []
    assert orchestrator.manager.secret.secret_messages == []


@pytest.mark.asyncio
async def test_secret_exit_discards_branch_before_next_normal_turn(
    orchestrator: ChatOrchestrator,
) -> None:
    chat_data = _base_chat()
    orchestrator.manager.switch_chat("/test/chat.json", chat_data)
    orchestrator.manager.secret.enter(list(chat_data.messages))

    await orchestrator.handle_ai_response(
        "secret a2",
        "/test/chat.json",
        chat_data,
        "secret",
        user_input="secret u2",
    )
    orchestrator.manager.secret.exit()

    send_action = await orchestrator.handle_user_message("u2")

    assert isinstance(send_action, SendAction)
    assert [message.content for message in send_action.messages] == [["u1"], ["a1"], ["u2"]]

    with patch.object(orchestrator.manager, "save_current_chat", new_callable=AsyncMock) as mock_save:
        result = await orchestrator.handle_ai_response(
            "a2",
            "/test/chat.json",
            chat_data,
            "normal",
            user_input="u2",
        )

    assert isinstance(result, ContinueAction)
    assert [message.content for message in chat_data.messages] == [["u1"], ["a1"], ["u2"], ["a2"]]
    mock_save.assert_called_once()


@pytest.mark.asyncio
async def test_secret_exit_clears_secret_error_before_normal_turn(
    orchestrator: ChatOrchestrator,
) -> None:
    chat_data = _base_chat()
    orchestrator.manager.switch_chat("/test/chat.json", chat_data)
    orchestrator.manager.secret.enter(list(chat_data.messages))

    await orchestrator.handle_ai_error(
        RuntimeError("secret timeout"),
        "/test/chat.json",
        chat_data,
        "secret",
        user_input="secret u2",
    )
    orchestrator.manager.secret.exit()

    action = await orchestrator.handle_user_message("u2")

    assert isinstance(action, SendAction)
    assert [message.content for message in action.messages] == [["u1"], ["a1"], ["u2"]]
    assert [message.role for message in chat_data.messages] == ["user", "assistant", "user"]
    assert [message.content for message in chat_data.messages] == [["u1"], ["a1"], ["u2"]]
