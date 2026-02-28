"""Tests for ChatOrchestrator."""

import pytest
from unittest.mock import AsyncMock, patch

from polychat.commands.types import CommandSignal
from polychat.domain.chat import ChatDocument, ChatMessage
from polychat.orchestrator import ChatOrchestrator
from polychat.orchestration.types import (
    BreakAction,
    ContinueAction,
    PrintAction,
    SendAction,
)
from polychat.session_manager import SessionManager
from test_helpers import make_profile


@pytest.fixture
def session_manager():
    """Create a test session manager."""
    manager = SessionManager(
        profile=make_profile(
            chats_dir="/test/chats",
            logs_dir="/test/logs",
        ),
        current_ai="claude",
        current_model="claude-haiku-4-5",
    )
    return manager


@pytest.fixture
def orchestrator(session_manager):
    """Create a test orchestrator."""
    return ChatOrchestrator(session_manager)


@pytest.fixture
def sample_chat_data():
    """Create sample chat data."""
    return ChatDocument.from_raw({
        "metadata": {
            "title": "Test Chat",
            "created_utc": "2026-02-02T00:00:00Z",
        },
        "messages": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there", "model": "claude-haiku-4-5"},
        ],
    })


class TestOrchestratorActionTypes:
    """Test typed orchestrator actions."""

    def test_create_continue_action(self):
        """Test creating a continue action."""
        action = ContinueAction(message="Test message")

        assert isinstance(action, ContinueAction)
        assert action.kind == "continue"
        assert action.message == "Test message"

    def test_create_break_action(self):
        """Test creating a break action."""
        action = BreakAction()

        assert isinstance(action, BreakAction)
        assert action.kind == "break"

    def test_create_continue_action_without_message(self):
        """Test creating action without message."""
        action = ContinueAction()

        assert isinstance(action, ContinueAction)
        assert action.kind == "continue"
        assert action.message is None


class TestExitSignal:
    """Test exit signal handling."""

    @pytest.mark.asyncio
    async def test_exit_signal(self, orchestrator):
        """Test that exit signal returns break action."""
        action = await orchestrator.handle_command_response(
            CommandSignal(kind="exit"),
        )

        assert isinstance(action, BreakAction)


class TestNewChatSignal:
    """Test new-chat signal handling."""

    @pytest.mark.asyncio
    async def test_new_chat_signal(self, orchestrator, sample_chat_data):
        """Test creating new chat."""
        orchestrator.manager.switch_chat("/test/old-chat.json", sample_chat_data)
        with patch("polychat.orchestration.chat_switching.load_chat") as mock_load_chat:
            mock_load_chat.return_value = ChatDocument.from_raw({"metadata": {}, "messages": []})
            with patch.object(orchestrator.manager, "save_current_chat", new_callable=AsyncMock) as mock_save:
                action = await orchestrator.handle_command_response(
                    CommandSignal(kind="new_chat", chat_path="/test/new-chat.json"),
                )

                # Should save old chat then persist new chat file
                assert mock_save.await_count == 2

            # Should load new chat
            mock_load_chat.assert_called_once_with("/test/new-chat.json")

            # Should return continue action with new chat
            assert isinstance(action, ContinueAction)
            assert "Created and opened new chat" in action.message
            assert orchestrator.manager.chat_path == "/test/new-chat.json"

    @pytest.mark.asyncio
    async def test_new_chat_without_current_chat(self, orchestrator):
        """Test creating new chat when no current chat."""
        with patch("polychat.orchestration.chat_switching.load_chat") as mock_load_chat:
            mock_load_chat.return_value = ChatDocument.from_raw({"metadata": {}, "messages": []})
            with patch.object(orchestrator.manager, "save_current_chat", new_callable=AsyncMock) as mock_save:
                action = await orchestrator.handle_command_response(
                    CommandSignal(kind="new_chat", chat_path="/test/new-chat.json"),
                )

                # Should persist newly created chat file
                mock_save.assert_called_once()

            # Should load new chat
            mock_load_chat.assert_called_once_with("/test/new-chat.json")

            assert isinstance(action, ContinueAction)
            assert orchestrator.manager.chat_path == "/test/new-chat.json"


class TestOpenChatSignal:
    """Test open-chat signal handling."""

    @pytest.mark.asyncio
    async def test_open_chat_signal(self, orchestrator, sample_chat_data):
        """Test opening existing chat."""
        orchestrator.manager.switch_chat("/test/current-chat.json", sample_chat_data)
        with patch("polychat.orchestration.chat_switching.load_chat") as mock_load_chat:
            mock_load_chat.return_value = ChatDocument.from_raw({"metadata": {}, "messages": [{"role": "user", "content": "Test"}]})
            with patch.object(orchestrator.manager, "save_current_chat", new_callable=AsyncMock) as mock_save:
                action = await orchestrator.handle_command_response(
                    CommandSignal(kind="open_chat", chat_path="/test/existing-chat.json"),
                )

                # Should save current chat
                mock_save.assert_called_once()

            # Should load selected chat
            mock_load_chat.assert_called_once_with("/test/existing-chat.json")

            # Should return continue action
            assert isinstance(action, ContinueAction)
            assert orchestrator.manager.chat_path == "/test/existing-chat.json"
            assert "Opened chat" in action.message


class TestCloseChatSignal:
    """Test close-chat signal handling."""

    @pytest.mark.asyncio
    async def test_close_chat_signal(self, orchestrator, sample_chat_data):
        """Test closing current chat."""
        orchestrator.manager.switch_chat("/test/chat.json", sample_chat_data)
        with patch.object(orchestrator.manager, "save_current_chat", new_callable=AsyncMock) as mock_save:
            action = await orchestrator.handle_command_response(
                CommandSignal(kind="close_chat"),
            )

            # Should save chat before closing
            mock_save.assert_called_once()

            # Should return continue action with empty chat
            assert isinstance(action, ContinueAction)
            assert orchestrator.manager.chat_path is None
            assert isinstance(orchestrator.manager.chat, ChatDocument)
            assert action.message == "Chat closed"

    @pytest.mark.asyncio
    async def test_close_chat_when_no_chat_open(self, orchestrator):
        """Test closing when no chat is open."""
        with patch.object(orchestrator.manager, "save_current_chat", new_callable=AsyncMock) as mock_save:
            action = await orchestrator.handle_command_response(
                CommandSignal(kind="close_chat"),
            )

            # Should not try to save
            mock_save.assert_not_called()

            # Should still return action
            assert isinstance(action, ContinueAction)
            assert orchestrator.manager.chat_path is None


class TestRenameChatSignal:
    """Test rename-current signal handling."""

    @pytest.mark.asyncio
    async def test_rename_current_signal(self, orchestrator):
        """Test renaming current chat."""
        orchestrator.manager.chat_path = "/test/old-chat.json"
        action = await orchestrator.handle_command_response(
            CommandSignal(kind="rename_current", chat_path="/test/renamed-chat.json"),
        )

        assert isinstance(action, ContinueAction)
        assert orchestrator.manager.chat_path == "/test/renamed-chat.json"
        assert "Renamed to" in action.message


class TestDeleteChatSignal:
    """Test delete-current signal handling."""

    @pytest.mark.asyncio
    async def test_delete_current_signal(self, orchestrator, sample_chat_data):
        """Test deleting current chat."""
        orchestrator.manager.switch_chat("/test/test-chat.json", sample_chat_data)
        action = await orchestrator.handle_command_response(
            CommandSignal(kind="delete_current", value="test-chat.json"),
        )

        # Should clear chat and return action
        assert isinstance(action, ContinueAction)
        assert orchestrator.manager.chat_path is None
        assert isinstance(orchestrator.manager.chat, ChatDocument)
        assert "Deleted" in action.message


class TestRetryModeSignals:
    """Test retry mode signal handling."""

    @pytest.mark.asyncio
    async def test_apply_retry_signal(self, orchestrator, sample_chat_data):
        """Test applying retry."""
        # Enter retry mode first
        orchestrator.manager.switch_chat("/test/chat.json", sample_chat_data)
        orchestrator.manager.enter_retry_mode(
            [ChatMessage.new_user("Original")],
            target_index=1,
        )
        retry_hex_id = orchestrator.manager.add_retry_attempt("Retry question", "Retry answer")
        original_hex_id = sample_chat_data.messages[1].hex_id

        with patch.object(orchestrator.manager, "save_current_chat", new_callable=AsyncMock) as mock_save:
            action = await orchestrator.handle_command_response(
                CommandSignal(kind="apply_retry", value=retry_hex_id),
            )

            # Should save chat
            mock_save.assert_called_once()

        # Should return print action
        assert isinstance(action, PrintAction)
        assert f"Applied retry [{retry_hex_id}]" == action.message

        # Should replace retried turn with retry user + selected assistant response.
        assert len(sample_chat_data.messages) == 2
        updated_user = sample_chat_data.messages[0]
        updated_assistant = sample_chat_data.messages[1]
        assert updated_user.role == "user"
        assert updated_user.content == ["Retry question"]
        assert updated_assistant.role == "assistant"
        assert updated_assistant.content == ["Retry answer"]
        assert updated_assistant.hex_id == original_hex_id

        # Should exit retry mode
        assert orchestrator.manager.retry_mode is False

    @pytest.mark.asyncio
    async def test_apply_retry_preserves_citations(self, orchestrator, sample_chat_data):
        """Applied retry should persist citations when available."""
        orchestrator.manager.switch_chat("/test/chat.json", sample_chat_data)
        orchestrator.manager.enter_retry_mode(
            [ChatMessage.new_user("Original")],
            target_index=1,
        )
        retry_hex_id = orchestrator.manager.add_retry_attempt(
            "Retry question",
            "Retry answer",
            citations=[{"url": "https://example.com", "title": "Example"}],
        )

        with patch.object(orchestrator.manager, "save_current_chat", new_callable=AsyncMock):
            action = await orchestrator.handle_command_response(
                CommandSignal(kind="apply_retry", value=retry_hex_id),
            )

        assert isinstance(action, PrintAction)
        assert sample_chat_data.messages[0].content == ["Retry question"]
        assert sample_chat_data.messages[1].citations == [
            {"url": "https://example.com", "title": "Example"}
        ]

    @pytest.mark.asyncio
    async def test_apply_retry_replaces_failed_user_error_turn(self, orchestrator):
        """Applying retry after an error should replace failed user+error with user+assistant."""
        chat_data = ChatDocument.from_raw({
            "metadata": {},
            "messages": [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "hi"},
                {"role": "user", "content": "broken request"},
                {"role": "error", "content": "timeout"},
            ],
        })
        orchestrator.manager.switch_chat("/test/chat.json", chat_data)
        orchestrator.manager.enter_retry_mode(
            [ChatMessage.new_user("hello"), ChatMessage.new_assistant("hi", model="test-model")],
            target_index=3,
        )
        retry_hex_id = orchestrator.manager.add_retry_attempt("try again", "done")

        with patch.object(orchestrator.manager, "save_current_chat", new_callable=AsyncMock):
            action = await orchestrator.handle_command_response(
                CommandSignal(kind="apply_retry", value=retry_hex_id),
            )

        assert isinstance(action, PrintAction)
        assert len(chat_data.messages) == 4
        assert chat_data.messages[2].role == "user"
        assert chat_data.messages[2].content == ["try again"]
        assert chat_data.messages[3].role == "assistant"
        assert chat_data.messages[3].model == orchestrator.manager.current_model
        assert chat_data.messages[3].content == ["done"]

    @pytest.mark.asyncio
    async def test_apply_retry_replaces_only_trailing_error_after_good_pair(self, orchestrator):
        """Applying retry should treat trailing error as standalone and keep prior good pair."""
        chat_data = ChatDocument.from_raw({
            "metadata": {},
            "messages": [
                {"role": "user", "content": "good user"},
                {"role": "assistant", "content": "good assistant"},
                {"role": "error", "content": "timeout"},
            ],
        })
        orchestrator.manager.switch_chat("/test/chat.json", chat_data)
        orchestrator.manager.enter_retry_mode(
            [ChatMessage.new_user("good user"), ChatMessage.new_assistant("good assistant", model="test-model")],
            target_index=2,
        )
        retry_hex_id = orchestrator.manager.add_retry_attempt("retry user", "retry answer")

        with patch.object(orchestrator.manager, "save_current_chat", new_callable=AsyncMock):
            action = await orchestrator.handle_command_response(
                CommandSignal(kind="apply_retry", value=retry_hex_id),
            )

        assert isinstance(action, PrintAction)
        assert len(chat_data.messages) == 4
        assert chat_data.messages[0].role == "user"
        assert chat_data.messages[0].content == ["good user"]
        assert chat_data.messages[1].role == "assistant"
        assert chat_data.messages[1].content == ["good assistant"]
        assert chat_data.messages[2].role == "user"
        assert chat_data.messages[2].content == ["retry user"]
        assert chat_data.messages[3].role == "assistant"
        assert chat_data.messages[3].content == ["retry answer"]

    @pytest.mark.asyncio
    async def test_apply_retry_when_not_in_retry_mode(self, orchestrator):
        """Test applying retry when not in retry mode."""
        action = await orchestrator.handle_command_response(
            CommandSignal(kind="apply_retry", value="abc"),
        )

        assert isinstance(action, PrintAction)
        assert "Not in retry mode" in action.message

    @pytest.mark.asyncio
    async def test_cancel_retry_signal(self, orchestrator):
        """Test cancelling retry mode."""
        # Enter retry mode first
        orchestrator.manager.enter_retry_mode([ChatMessage.new_user("Test")])

        action = await orchestrator.handle_command_response(
            CommandSignal(kind="cancel_retry"),
        )

        assert isinstance(action, PrintAction)
        assert "Cancelled retry mode" in action.message
        assert orchestrator.manager.retry_mode is False

    @pytest.mark.asyncio
    async def test_cancel_retry_when_not_in_retry_mode(self, orchestrator):
        """Test cancelling retry when not in retry mode."""
        action = await orchestrator.handle_command_response(
            CommandSignal(kind="cancel_retry"),
        )

        assert isinstance(action, PrintAction)
        assert "Not in retry mode" in action.message


class TestSecretModeSignals:
    """Test secret mode signal handling."""

    @pytest.mark.asyncio
    async def test_clear_secret_context_when_in_secret_mode(self, orchestrator):
        """Test clearing secret context when in secret mode."""
        # Enter secret mode first
        orchestrator.manager.enter_secret_mode([ChatMessage.new_user("Base")])

        action = await orchestrator.handle_command_response(
            CommandSignal(kind="clear_secret_context"),
        )

        assert isinstance(action, PrintAction)
        assert "Secret mode disabled" in action.message
        assert orchestrator.manager.secret_mode is False

    @pytest.mark.asyncio
    async def test_clear_secret_context_when_not_in_secret_mode(self, orchestrator):
        """Test clearing secret context when not in secret mode."""
        action = await orchestrator.handle_command_response(
            CommandSignal(kind="clear_secret_context"),
        )

        assert isinstance(action, ContinueAction)
        assert action.message is None



class TestInvalidSignalPayloads:
    """Test signal-payload validation and unknown signal handling."""

    @pytest.mark.asyncio
    async def test_new_chat_signal_missing_path(self, orchestrator):
        action = await orchestrator.handle_command_response(
            CommandSignal(kind="new_chat"),
        )

        assert isinstance(action, PrintAction)
        assert action.message == "Error: Invalid command signal (missing new chat path)"

    @pytest.mark.asyncio
    async def test_open_chat_signal_missing_path(self, orchestrator):
        action = await orchestrator.handle_command_response(
            CommandSignal(kind="open_chat"),
        )

        assert isinstance(action, PrintAction)
        assert action.message == "Error: Invalid command signal (missing open chat path)"

    @pytest.mark.asyncio
    async def test_rename_current_signal_missing_path(self, orchestrator):
        action = await orchestrator.handle_command_response(
            CommandSignal(kind="rename_current"),
        )

        assert isinstance(action, PrintAction)
        assert action.message == "Error: Invalid command signal (missing rename path)"

    @pytest.mark.asyncio
    async def test_delete_current_signal_missing_filename(self, orchestrator):
        action = await orchestrator.handle_command_response(
            CommandSignal(kind="delete_current"),
        )

        assert isinstance(action, PrintAction)
        assert action.message == "Error: Invalid command signal (missing deleted filename)"

    @pytest.mark.asyncio
    async def test_apply_retry_signal_missing_or_blank_id(self, orchestrator):
        missing_id = await orchestrator.handle_command_response(
            CommandSignal(kind="apply_retry"),
        )
        blank_id = await orchestrator.handle_command_response(
            CommandSignal(kind="apply_retry", value="   "),
        )

        assert isinstance(missing_id, PrintAction)
        assert missing_id.message == "Retry ID not found"
        assert isinstance(blank_id, PrintAction)
        assert blank_id.message == "Retry ID not found"

    @pytest.mark.asyncio
    async def test_unknown_signal_kind(self, orchestrator):
        action = await orchestrator.handle_command_response(
            CommandSignal(kind="unknown"),  # type: ignore[arg-type]
        )

        assert isinstance(action, PrintAction)
        assert action.message == "Error: Unknown command signal 'unknown'"


class TestRegularMessages:
    """Test handling of regular (non-signal) messages."""

    @pytest.mark.asyncio
    async def test_regular_message_is_printed(self, orchestrator):
        """Test that regular messages are printed."""
        action = await orchestrator.handle_command_response(
            "This is a regular message",
        )

        assert isinstance(action, PrintAction)
        assert action.message == "This is a regular message"

    @pytest.mark.asyncio
    async def test_empty_message(self, orchestrator):
        """Test handling empty message."""
        action = await orchestrator.handle_command_response(
            "",
        )

        assert isinstance(action, PrintAction)
        assert action.message == ""

    @pytest.mark.asyncio
    async def test_pending_error_message_excludes_secret_guidance(self, orchestrator):
        """Pending-error guidance should point to retry/rewind only."""
        chat_data = ChatDocument.from_raw({
            "metadata": {},
            "messages": [
                {"role": "user", "content": ["hello"]},
                {"role": "error", "content": ["oops"]},
            ],
        })
        orchestrator.manager.switch_chat("/test/chat.json", chat_data)

        action = await orchestrator.handle_user_message("new input")

        assert isinstance(action, PrintAction)
        assert "/retry" in action.message
        assert "/rewind" in action.message
        assert "/secret" not in action.message

    @pytest.mark.asyncio
    async def test_regular_message_saves_chat(self, orchestrator, sample_chat_data):
        """Regular command responses should save chat changes."""
        orchestrator.manager.switch_chat("/test/chat.json", sample_chat_data)
        with patch.object(orchestrator.manager, "save_current_chat", new_callable=AsyncMock) as mock_save:
            action = await orchestrator.handle_command_response(
                "Updated title",
            )

            assert isinstance(action, PrintAction)
            assert action.message == "Updated title"
            mock_save.assert_called_once()


class TestRetryModeMessages:
    """Test retry-mode message preparation."""

    @pytest.mark.asyncio
    async def test_retry_mode_send_excludes_retried_user_assistant_pair(self, orchestrator):
        chat_data = ChatDocument.from_raw({
            "metadata": {},
            "messages": [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "hello!"},
                {"role": "user", "content": "nice to meet you"},
                {"role": "assistant", "content": "nice to meet you too!"},
            ],
        })
        orchestrator.manager.switch_chat("/test/chat.json", chat_data)
        orchestrator.manager.enter_retry_mode(
            [
                ChatMessage.new_user("hello"),
                ChatMessage.new_assistant("hello!", model="test-model"),
            ],
            target_index=3,
        )

        action = await orchestrator.handle_user_message("what did i just say?")

        assert isinstance(action, SendAction)
        assert action.mode == "retry"
        assert len(action.messages) == 3
        assert action.messages[0].role == "user"
        assert action.messages[0].content == ["hello"]
        assert action.messages[1].role == "assistant"
        assert action.messages[1].content == ["hello!"]
        assert action.messages[2].role == "user"
        assert action.messages[2].content == ["what did i just say?"]


class TestSessionManagerIntegration:
    """Test integration with SessionManager."""

    @pytest.mark.asyncio
    async def test_chat_switching_updates_session_manager(self, orchestrator):
        """Test that chat switching updates the session manager."""
        with patch("polychat.orchestration.chat_switching.load_chat") as mock_load_chat:
            mock_load_chat.return_value = ChatDocument.from_raw({
                "metadata": {
                    "title": None,
                    "summary": None,
                    "system_prompt": None,
                    "created_utc": None,
                    "updated_utc": None,
                },
                "messages": [],
            })

            with patch.object(orchestrator.manager, "save_current_chat", new_callable=AsyncMock):
                await orchestrator.handle_command_response(
                    CommandSignal(kind="new_chat", chat_path="/test/new.json"),
                )

            # Session manager should be updated
            assert orchestrator.manager.chat.messages == []

    @pytest.mark.asyncio
    async def test_close_chat_clears_session_manager(self, orchestrator, sample_chat_data):
        """Test that closing chat clears session manager."""
        # Set up with a chat
        orchestrator.manager.switch_chat("/test/chat.json", sample_chat_data)

        with patch.object(orchestrator.manager, "save_current_chat", new_callable=AsyncMock):
            await orchestrator.handle_command_response(
                CommandSignal(kind="close_chat"),
            )

            # Session manager chat should be empty
            assert isinstance(orchestrator.manager.chat, ChatDocument)


class TestCancelHandling:
    @pytest.mark.asyncio
    async def test_handle_user_cancel_normal_mode_saves_consistent_chat(self, orchestrator):
        chat_data = ChatDocument.from_raw({
            "metadata": {"title": "Cancel Test"},
            "messages": [{"role": "user", "content": "pending"}],
        })

        with patch.object(orchestrator.manager, "save_current_chat", new_callable=AsyncMock) as mock_save:
            action = await orchestrator.handle_user_cancel(
                chat_data,
                "normal",
                chat_path="/test/chat.json",
            )

            assert isinstance(action, PrintAction)
            assert chat_data.messages == []
            mock_save.assert_awaited_once_with(
                chat_path="/test/chat.json",
                chat_data=chat_data,
            )

    @pytest.mark.asyncio
    async def test_handle_user_cancel_retry_mode_does_not_save(self, orchestrator):
        chat_data = ChatDocument.from_raw({"metadata": {}, "messages": []})

        with patch.object(orchestrator.manager, "save_current_chat", new_callable=AsyncMock) as mock_save:
            action = await orchestrator.handle_user_cancel(chat_data, "retry")

            assert isinstance(action, PrintAction)
            mock_save.assert_not_called()


class TestPreSendValidationRollback:
    @pytest.mark.asyncio
    async def test_normal_mode_rolls_back_pending_user_message(self, orchestrator):
        chat_data = ChatDocument.from_raw({
            "metadata": {"title": "Validation rollback"},
            "messages": [{"role": "assistant", "content": ["existing"]}],
        })
        orchestrator.manager.switch_chat("/test/chat.json", chat_data)

        action = await orchestrator._handle_normal_message(
            "unsent user input",
        )

        assert isinstance(action, SendAction)
        assert action.mode == "normal"
        assert chat_data.messages[-1].role == "user"

        with patch.object(orchestrator.manager, "save_current_chat", new_callable=AsyncMock) as mock_save:
            rolled_back = await orchestrator.rollback_pre_send_failure(
                chat_path="/test/chat.json",
                chat_data=chat_data,
                mode="normal",
            )

            assert rolled_back is True
            assert len(chat_data.messages) == 1
            assert chat_data.messages[-1].role == "assistant"
            mock_save.assert_awaited_once_with(
                chat_path="/test/chat.json",
                chat_data=chat_data,
            )

    @pytest.mark.asyncio
    async def test_non_normal_mode_does_not_mutate_chat(self, orchestrator):
        chat_data = ChatDocument.from_raw({
            "metadata": {},
            "messages": [{"role": "user", "content": ["base"]}],
        })
        orchestrator.manager._state.hex_id_set.add("abc")

        with patch.object(orchestrator.manager, "save_current_chat", new_callable=AsyncMock) as mock_save:
            rolled_back = await orchestrator.rollback_pre_send_failure(
                chat_path="/test/chat.json",
                chat_data=chat_data,
                mode="retry",
                assistant_hex_id="abc",
            )

            assert rolled_back is False
            assert len(chat_data.messages) == 1
            assert "abc" not in orchestrator.manager.hex_id_set
            mock_save.assert_not_called()


class TestSecretModeContext:
    @pytest.mark.asyncio
    async def test_secret_mode_uses_current_chat_history_each_turn(self, orchestrator):
        chat_data = ChatDocument.from_raw({
            "metadata": {},
            "messages": [
                {"role": "user", "content": ["u1"]},
                {"role": "assistant", "content": ["a1"]},
            ],
        })
        orchestrator.manager.switch_chat("/test/chat.json", chat_data)
        orchestrator.manager.enter_secret_mode(list(chat_data.messages))

        first = await orchestrator.handle_user_message("secret one")
        assert isinstance(first, SendAction)
        assert [m.content for m in first.messages[:-1]] == [["u1"], ["a1"]]

        # Simulate persisted history changing between secret turns.
        from polychat.domain.chat import ChatMessage as _CM
        chat_data.messages.append(_CM.from_raw({"role": "user", "content": ["u2"]}))
        chat_data.messages.append(_CM.from_raw({"role": "assistant", "content": ["a2"]}))

        second = await orchestrator.handle_user_message("secret two")
        assert isinstance(second, SendAction)
        assert [m.content for m in second.messages[:-1]] == [["u1"], ["a1"], ["u2"], ["a2"]]
