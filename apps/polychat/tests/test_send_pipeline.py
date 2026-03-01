"""Tests for REPL send-pipeline execution paths."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from polychat.domain.chat import ChatDocument
from polychat.orchestrator import ChatOrchestrator
from polychat.orchestration.types import ContinueAction, PrintAction, SendAction
from polychat.repl.send_pipeline import execute_send_action
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


def _chat_with_existing_assistant() -> ChatDocument:
    return ChatDocument.from_raw({
        "metadata": {},
        "messages": [
            {"role": "assistant", "content": "existing context", "model": "claude-haiku-4-5"},
        ],
    })


async def _build_normal_send_action(orchestrator: ChatOrchestrator) -> tuple[SendAction, ChatDocument]:
    chat_data = _chat_with_existing_assistant()
    orchestrator.manager.switch_chat("/test/chat.json", chat_data)
    action = await orchestrator.handle_user_message("unsent user input")
    assert isinstance(action, SendAction)
    assert action.mode == "normal"
    return action, chat_data


def _empty_stream():
    async def _iter():
        if False:
            yield ""

    return _iter()


@pytest.mark.asyncio
async def test_execute_send_action_rolls_back_pre_send_validation_failure(
    orchestrator: ChatOrchestrator,
    capsys: pytest.CaptureFixture[str],
) -> None:
    action, chat_data = await _build_normal_send_action(orchestrator)

    with (
        patch(
            "polychat.repl.send_pipeline.validate_and_get_provider",
            return_value=(None, "No API key configured for claude"),
        ),
        patch("polychat.repl.send_pipeline.send_message_to_ai", new_callable=AsyncMock) as mock_send,
        patch.object(
            orchestrator.manager,
            "save_current_chat",
            new_callable=AsyncMock,
        ) as mock_save,
    ):
        await execute_send_action(
            action,
            manager=orchestrator.manager,
            orchestrator=orchestrator,
        )

    assert [message.role for message in chat_data.messages] == ["assistant", "error"]
    assert chat_data.messages[-1].content == ["No API key configured for claude"]
    mock_send.assert_not_awaited()
    mock_save.assert_awaited_once_with(
        chat_path="/test/chat.json",
        chat_data=chat_data,
    )
    output = capsys.readouterr().out
    assert "Error: No API key configured for claude" in output


@pytest.mark.asyncio
async def test_execute_send_action_rolls_back_internal_provider_resolution_failure(
    orchestrator: ChatOrchestrator,
    capsys: pytest.CaptureFixture[str],
) -> None:
    action, chat_data = await _build_normal_send_action(orchestrator)

    with (
        patch(
            "polychat.repl.send_pipeline.validate_and_get_provider",
            return_value=(None, None),
        ),
        patch("polychat.repl.send_pipeline.send_message_to_ai", new_callable=AsyncMock) as mock_send,
        patch.object(
            orchestrator.manager,
            "save_current_chat",
            new_callable=AsyncMock,
        ) as mock_save,
    ):
        await execute_send_action(
            action,
            manager=orchestrator.manager,
            orchestrator=orchestrator,
        )

    assert [message.role for message in chat_data.messages] == ["assistant", "error"]
    assert chat_data.messages[-1].content == ["Provider resolution failed unexpectedly"]
    mock_send.assert_not_awaited()
    mock_save.assert_awaited_once_with(
        chat_path="/test/chat.json",
        chat_data=chat_data,
    )
    output = capsys.readouterr().out
    assert "Error: Provider resolution failed unexpectedly" in output


@pytest.mark.asyncio
async def test_execute_send_action_routes_keyboard_interrupt_to_cancel_handler(
    orchestrator: ChatOrchestrator,
    capsys: pytest.CaptureFixture[str],
) -> None:
    action, chat_data = await _build_normal_send_action(orchestrator)

    with (
        patch(
            "polychat.repl.send_pipeline.validate_and_get_provider",
            return_value=(object(), None),
        ),
        patch(
            "polychat.repl.send_pipeline.send_message_to_ai",
            new_callable=AsyncMock,
            return_value=(_empty_stream(), {"started": 0.0}),
        ),
        patch(
            "polychat.repl.send_pipeline.display_streaming_response",
            new_callable=AsyncMock,
            side_effect=KeyboardInterrupt,
        ),
        patch.object(
            orchestrator,
            "handle_user_cancel",
            new_callable=AsyncMock,
            return_value=PrintAction(message="[Message cancelled]"),
        ) as mock_cancel,
    ):
        await execute_send_action(
            action,
            manager=orchestrator.manager,
            orchestrator=orchestrator,
        )

    mock_cancel.assert_awaited_once_with(
        chat_data,
        "normal",
        chat_path="/test/chat.json",
        assistant_hex_id=None,
    )
    assert "[Message cancelled]" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_execute_send_action_routes_runtime_error_to_error_handler(
    orchestrator: ChatOrchestrator,
    capsys: pytest.CaptureFixture[str],
) -> None:
    action, chat_data = await _build_normal_send_action(orchestrator)
    error = RuntimeError("network down")

    with (
        patch(
            "polychat.repl.send_pipeline.validate_and_get_provider",
            return_value=(object(), None),
        ),
        patch(
            "polychat.repl.send_pipeline.send_message_to_ai",
            new_callable=AsyncMock,
            side_effect=error,
        ),
        patch.object(
            orchestrator,
            "handle_ai_error",
            new_callable=AsyncMock,
            return_value=PrintAction(message="Error: network down"),
        ) as mock_error,
    ):
        await execute_send_action(
            action,
            manager=orchestrator.manager,
            orchestrator=orchestrator,
        )

    mock_error.assert_awaited_once_with(
        error,
        "/test/chat.json",
        chat_data,
        "normal",
        user_input=None,
        assistant_hex_id=None,
    )
    assert "Error: network down" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_execute_send_action_treats_citation_failure_as_nonfatal_warning(
    orchestrator: ChatOrchestrator,
    capsys: pytest.CaptureFixture[str],
) -> None:
    action, chat_data = await _build_normal_send_action(orchestrator)
    metadata = {
        "started": 0.0,
        "citations": [{"url": "https://example.com", "title": "Example"}],
    }

    with (
        patch(
            "polychat.repl.send_pipeline.validate_and_get_provider",
            return_value=(object(), None),
        ),
        patch(
            "polychat.repl.send_pipeline.send_message_to_ai",
            new_callable=AsyncMock,
            return_value=(_empty_stream(), metadata),
        ),
        patch(
            "polychat.repl.send_pipeline.display_streaming_response",
            new_callable=AsyncMock,
            return_value=("response text", 0.2),
        ),
        patch(
            "polychat.repl.send_pipeline._process_citations",
            new_callable=AsyncMock,
            side_effect=RuntimeError("citation failed sk-1234567890abcdefghijk"),
        ),
        patch("polychat.repl.send_pipeline._log_response_metrics"),
        patch.object(
            orchestrator,
            "handle_ai_response",
            new_callable=AsyncMock,
            return_value=ContinueAction(),
        ) as mock_handle_response,
        patch.object(
            orchestrator,
            "handle_ai_error",
            new_callable=AsyncMock,
        ) as mock_handle_error,
    ):
        await execute_send_action(
            action,
            manager=orchestrator.manager,
            orchestrator=orchestrator,
        )

    mock_handle_error.assert_not_awaited()
    mock_handle_response.assert_awaited_once_with(
        "response text",
        "/test/chat.json",
        chat_data,
        "normal",
        user_input=None,
        assistant_hex_id=None,
        citations=[{"number": 1, "url": "https://example.com", "title": "Example"}],
    )
    output = capsys.readouterr().out
    assert "[Warning: citation processing failed: citation failed [REDACTED_API_KEY]]" in output


@pytest.mark.asyncio
async def test_execute_send_action_treats_metrics_failure_as_nonfatal_warning(
    orchestrator: ChatOrchestrator,
) -> None:
    action, chat_data = await _build_normal_send_action(orchestrator)
    metadata = {"started": 0.0}

    with (
        patch(
            "polychat.repl.send_pipeline.validate_and_get_provider",
            return_value=(object(), None),
        ),
        patch(
            "polychat.repl.send_pipeline.send_message_to_ai",
            new_callable=AsyncMock,
            return_value=(_empty_stream(), metadata),
        ),
        patch(
            "polychat.repl.send_pipeline.display_streaming_response",
            new_callable=AsyncMock,
            return_value=("response text", 0.2),
        ),
        patch(
            "polychat.repl.send_pipeline._process_citations",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "polychat.repl.send_pipeline._log_response_metrics",
            side_effect=RuntimeError("metrics failed sk-1234567890abcdefghijk"),
        ),
        patch("polychat.repl.send_pipeline.logging.warning") as mock_warning,
        patch.object(
            orchestrator,
            "handle_ai_response",
            new_callable=AsyncMock,
            return_value=ContinueAction(),
        ) as mock_handle_response,
        patch.object(
            orchestrator,
            "handle_ai_error",
            new_callable=AsyncMock,
        ) as mock_handle_error,
    ):
        await execute_send_action(
            action,
            manager=orchestrator.manager,
            orchestrator=orchestrator,
        )

    mock_handle_error.assert_not_awaited()
    mock_handle_response.assert_awaited_once_with(
        "response text",
        "/test/chat.json",
        chat_data,
        "normal",
        user_input=None,
        assistant_hex_id=None,
        citations=[],
    )
    mock_warning.assert_called_once_with(
        "Non-fatal AI response post-processing failure (%s): %s",
        "response_metrics_logging",
        "metrics failed [REDACTED_API_KEY]",
    )
