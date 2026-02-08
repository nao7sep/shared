"""Tests for ChatOrchestrator."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.poly_chat.orchestrator import ChatOrchestrator, OrchestratorAction
from src.poly_chat.session_manager import SessionManager


@pytest.fixture
def session_manager():
    """Create a test session manager."""
    manager = SessionManager(
        profile={"chats_dir": "/test/chats", "log_dir": "/test/logs"},
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
    return {
        "metadata": {
            "title": "Test Chat",
            "created_at": "2026-02-02T00:00:00Z",
        },
        "messages": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there", "model": "claude-haiku-4-5"},
        ],
    }


class TestOrchestratorAction:
    """Test OrchestratorAction dataclass."""

    def test_create_continue_action(self):
        """Test creating a continue action."""
        action = OrchestratorAction(action="continue", message="Test message")

        assert action.action == "continue"
        assert action.message == "Test message"
        assert action.chat_path is None
        assert action.chat_data is None
        assert action.error is None

    def test_create_break_action(self):
        """Test creating a break action."""
        action = OrchestratorAction(action="break")

        assert action.action == "break"
        assert action.message is None

    def test_create_action_with_chat_data(self):
        """Test creating action with chat data."""
        chat_data = {"messages": []}
        action = OrchestratorAction(
            action="continue",
            chat_path="/test/chat.json",
            chat_data=chat_data,
        )

        assert action.action == "continue"
        assert action.chat_path == "/test/chat.json"
        assert action.chat_data == chat_data


class TestExitSignal:
    """Test __EXIT__ signal handling."""

    @pytest.mark.asyncio
    async def test_exit_signal(self, orchestrator):
        """Test that __EXIT__ returns break action."""
        action = await orchestrator.handle_command_response(
            "__EXIT__",
            current_chat_path=None,
            current_chat_data=None,
        )

        assert action.action == "break"
        assert action.message is None


class TestNewChatSignal:
    """Test __NEW_CHAT__ signal handling."""

    @pytest.mark.asyncio
    async def test_new_chat_signal(self, orchestrator, sample_chat_data):
        """Test creating new chat."""
        with patch("src.poly_chat.orchestrator.chat") as mock_chat:
            mock_chat.load_chat = MagicMock(return_value={"messages": []})
            with patch.object(orchestrator.manager, "save_current_chat", new_callable=AsyncMock) as mock_save:
                action = await orchestrator.handle_command_response(
                    "__NEW_CHAT__:/test/new-chat.json",
                    current_chat_path="/test/old-chat.json",
                    current_chat_data=sample_chat_data,
                )

                # Should save old chat then persist new chat file
                assert mock_save.await_count == 2

            # Should load new chat
            mock_chat.load_chat.assert_called_once_with("/test/new-chat.json")

            # Should return continue action with new chat
            assert action.action == "continue"
            assert action.chat_path == "/test/new-chat.json"
            assert action.chat_data == {"messages": []}
            assert "Created new chat" in action.message

    @pytest.mark.asyncio
    async def test_new_chat_without_current_chat(self, orchestrator):
        """Test creating new chat when no current chat."""
        with patch("src.poly_chat.orchestrator.chat") as mock_chat:
            mock_chat.load_chat = MagicMock(return_value={"messages": []})
            with patch.object(orchestrator.manager, "save_current_chat", new_callable=AsyncMock) as mock_save:
                action = await orchestrator.handle_command_response(
                    "__NEW_CHAT__:/test/new-chat.json",
                    current_chat_path=None,
                    current_chat_data=None,
                )

                # Should persist newly created chat file
                mock_save.assert_called_once()

            # Should load new chat
            mock_chat.load_chat.assert_called_once_with("/test/new-chat.json")

            assert action.action == "continue"
            assert action.chat_path == "/test/new-chat.json"


class TestOpenChatSignal:
    """Test __OPEN_CHAT__ signal handling."""

    @pytest.mark.asyncio
    async def test_open_chat_signal(self, orchestrator, sample_chat_data):
        """Test opening existing chat."""
        with patch("src.poly_chat.orchestrator.chat") as mock_chat:
            mock_chat.load_chat = MagicMock(return_value={"messages": [{"role": "user", "content": "Test"}]})
            with patch.object(orchestrator.manager, "save_current_chat", new_callable=AsyncMock) as mock_save:
                action = await orchestrator.handle_command_response(
                    "__OPEN_CHAT__:/test/existing-chat.json",
                    current_chat_path="/test/current-chat.json",
                    current_chat_data=sample_chat_data,
                )

                # Should save current chat
                mock_save.assert_called_once()

            # Should load selected chat
            mock_chat.load_chat.assert_called_once_with("/test/existing-chat.json")

            # Should return continue action
            assert action.action == "continue"
            assert action.chat_path == "/test/existing-chat.json"
            assert "Opened chat" in action.message


class TestCloseChatSignal:
    """Test __CLOSE_CHAT__ signal handling."""

    @pytest.mark.asyncio
    async def test_close_chat_signal(self, orchestrator, sample_chat_data):
        """Test closing current chat."""
        with patch.object(orchestrator.manager, "save_current_chat", new_callable=AsyncMock) as mock_save:
            action = await orchestrator.handle_command_response(
                "__CLOSE_CHAT__",
                current_chat_path="/test/chat.json",
                current_chat_data=sample_chat_data,
            )

            # Should save chat before closing
            mock_save.assert_called_once()

            # Should return continue action with empty chat
            assert action.action == "continue"
            assert action.chat_path is None
            assert action.chat_data == {}
            assert action.message == "Chat closed"

    @pytest.mark.asyncio
    async def test_close_chat_when_no_chat_open(self, orchestrator):
        """Test closing when no chat is open."""
        with patch.object(orchestrator.manager, "save_current_chat", new_callable=AsyncMock) as mock_save:
            action = await orchestrator.handle_command_response(
                "__CLOSE_CHAT__",
                current_chat_path=None,
                current_chat_data=None,
            )

            # Should not try to save
            mock_save.assert_not_called()

            # Should still return action
            assert action.action == "continue"
            assert action.chat_path is None


class TestRenameChatSignal:
    """Test __RENAME_CURRENT__ signal handling."""

    @pytest.mark.asyncio
    async def test_rename_current_signal(self, orchestrator):
        """Test renaming current chat."""
        action = await orchestrator.handle_command_response(
            "__RENAME_CURRENT__:/test/renamed-chat.json",
            current_chat_path="/test/old-chat.json",
            current_chat_data={},
        )

        assert action.action == "continue"
        assert action.chat_path == "/test/renamed-chat.json"
        assert "Renamed to" in action.message


class TestDeleteChatSignal:
    """Test __DELETE_CURRENT__ signal handling."""

    @pytest.mark.asyncio
    async def test_delete_current_signal(self, orchestrator, sample_chat_data):
        """Test deleting current chat."""
        action = await orchestrator.handle_command_response(
            "__DELETE_CURRENT__:test-chat.json",
            current_chat_path="/test/test-chat.json",
            current_chat_data=sample_chat_data,
        )

        # Should clear chat and return action
        assert action.action == "continue"
        assert action.chat_path is None
        assert action.chat_data == {}
        assert "Deleted" in action.message


class TestRetryModeSignals:
    """Test retry mode signal handling."""

    @pytest.mark.asyncio
    async def test_apply_retry_signal(self, orchestrator, sample_chat_data):
        """Test applying retry."""
        # Enter retry mode first
        orchestrator.manager.enter_retry_mode([{"role": "user", "content": "Original"}])
        orchestrator.manager.set_retry_attempt("Retry question", "Retry answer")

        with patch("src.poly_chat.orchestrator.chat") as mock_chat:
            mock_chat.add_user_message = MagicMock()
            mock_chat.add_assistant_message = MagicMock()
            with patch.object(orchestrator.manager, "save_current_chat", new_callable=AsyncMock) as mock_save:
                action = await orchestrator.handle_command_response(
                    "__APPLY_RETRY__",
                    current_chat_path="/test/chat.json",
                    current_chat_data=sample_chat_data,
                )

                # Should save chat
                mock_save.assert_called_once()

            # Should return print action
            assert action.action == "print"
            assert "Applied retry" in action.message

            # Should exit retry mode
            assert orchestrator.manager.retry_mode is False

    @pytest.mark.asyncio
    async def test_apply_retry_when_not_in_retry_mode(self, orchestrator):
        """Test applying retry when not in retry mode."""
        action = await orchestrator.handle_command_response(
            "__APPLY_RETRY__",
            current_chat_path="/test/chat.json",
            current_chat_data={},
        )

        assert action.action == "print"
        assert "Not in retry mode" in action.message

    @pytest.mark.asyncio
    async def test_cancel_retry_signal(self, orchestrator):
        """Test cancelling retry mode."""
        # Enter retry mode first
        orchestrator.manager.enter_retry_mode([{"role": "user", "content": "Test"}])

        action = await orchestrator.handle_command_response(
            "__CANCEL_RETRY__",
            current_chat_path=None,
            current_chat_data=None,
        )

        assert action.action == "print"
        assert "Cancelled retry mode" in action.message
        assert orchestrator.manager.retry_mode is False

    @pytest.mark.asyncio
    async def test_cancel_retry_when_not_in_retry_mode(self, orchestrator):
        """Test cancelling retry when not in retry mode."""
        action = await orchestrator.handle_command_response(
            "__CANCEL_RETRY__",
            current_chat_path=None,
            current_chat_data=None,
        )

        assert action.action == "print"
        assert "Not in retry mode" in action.message


class TestSecretModeSignals:
    """Test secret mode signal handling."""

    @pytest.mark.asyncio
    async def test_clear_secret_context_when_in_secret_mode(self, orchestrator):
        """Test clearing secret context when in secret mode."""
        # Enter secret mode first
        orchestrator.manager.enter_secret_mode([{"role": "user", "content": "Base"}])

        action = await orchestrator.handle_command_response(
            "__CLEAR_SECRET_CONTEXT__",
            current_chat_path=None,
            current_chat_data=None,
        )

        assert action.action == "print"
        assert "Secret mode disabled" in action.message
        assert orchestrator.manager.secret_mode is False

    @pytest.mark.asyncio
    async def test_clear_secret_context_when_not_in_secret_mode(self, orchestrator):
        """Test clearing secret context when not in secret mode."""
        action = await orchestrator.handle_command_response(
            "__CLEAR_SECRET_CONTEXT__",
            current_chat_path=None,
            current_chat_data=None,
        )

        assert action.action == "continue"
        assert action.message is None

    @pytest.mark.asyncio
    async def test_secret_oneshot_signal(self, orchestrator):
        """Test secret oneshot message."""
        action = await orchestrator.handle_command_response(
            "__SECRET_ONESHOT__:What is the meaning of life?",
            current_chat_path=None,
            current_chat_data=None,
        )

        assert action.action == "secret_oneshot"
        assert action.message == "What is the meaning of life?"


class TestRegularMessages:
    """Test handling of regular (non-signal) messages."""

    @pytest.mark.asyncio
    async def test_regular_message_is_printed(self, orchestrator):
        """Test that regular messages are printed."""
        action = await orchestrator.handle_command_response(
            "This is a regular message",
            current_chat_path=None,
            current_chat_data=None,
        )

        assert action.action == "print"
        assert action.message == "This is a regular message"

    @pytest.mark.asyncio
    async def test_empty_message(self, orchestrator):
        """Test handling empty message."""
        action = await orchestrator.handle_command_response(
            "",
            current_chat_path=None,
            current_chat_data=None,
        )

        assert action.action == "print"
        assert action.message == ""

    @pytest.mark.asyncio
    async def test_regular_message_saves_when_chat_dirty(self, orchestrator, sample_chat_data):
        """Regular command responses should flush dirty chat changes."""
        orchestrator.manager.mark_chat_dirty()

        with patch.object(orchestrator.manager, "save_current_chat", new_callable=AsyncMock) as mock_save:
            action = await orchestrator.handle_command_response(
                "Updated title",
                current_chat_path="/test/chat.json",
                current_chat_data=sample_chat_data,
            )

            assert action.action == "print"
            assert action.message == "Updated title"
            mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_regular_message_skips_save_when_not_dirty(self, orchestrator, sample_chat_data):
        """Regular command responses should not save unless dirty."""
        with patch.object(orchestrator.manager, "save_current_chat", new_callable=AsyncMock) as mock_save:
            await orchestrator.handle_command_response(
                "No state mutation",
                current_chat_path="/test/chat.json",
                current_chat_data=sample_chat_data,
            )

            mock_save.assert_called_once()


class TestSessionManagerIntegration:
    """Test integration with SessionManager."""

    @pytest.mark.asyncio
    async def test_chat_switching_updates_session_manager(self, orchestrator):
        """Test that chat switching updates the session manager."""
        with patch("src.poly_chat.orchestrator.chat") as mock_chat:
            mock_chat.load_chat = MagicMock(
                return_value={
                    "metadata": {
                        "title": None,
                        "summary": None,
                        "system_prompt_path": None,
                        "default_model": None,
                        "created_at": None,
                        "updated_at": None,
                    },
                    "messages": [],
                }
            )

            initial_chat = orchestrator.manager.chat

            with patch.object(orchestrator.manager, "save_current_chat", new_callable=AsyncMock):
                await orchestrator.handle_command_response(
                    "__NEW_CHAT__:/test/new.json",
                    current_chat_path=None,
                    current_chat_data=None,
                )

            # Session manager should be updated
            assert orchestrator.manager.chat["messages"] == []

    @pytest.mark.asyncio
    async def test_close_chat_clears_session_manager(self, orchestrator, sample_chat_data):
        """Test that closing chat clears session manager."""
        # Set up with a chat
        orchestrator.manager.switch_chat("/test/chat.json", sample_chat_data)

        with patch.object(orchestrator.manager, "save_current_chat", new_callable=AsyncMock):
            await orchestrator.handle_command_response(
                "__CLOSE_CHAT__",
                current_chat_path="/test/chat.json",
                current_chat_data=sample_chat_data,
            )

            # Session manager chat should be empty
            assert orchestrator.manager.chat == {}


class TestCancelHandling:
    @pytest.mark.asyncio
    async def test_handle_user_cancel_normal_mode_saves_consistent_chat(self, orchestrator):
        chat_data = {
            "metadata": {"title": "Cancel Test"},
            "messages": [{"role": "user", "content": "pending"}],
        }

        with patch.object(orchestrator.manager, "save_current_chat", new_callable=AsyncMock) as mock_save:
            action = await orchestrator.handle_user_cancel(
                chat_data,
                "normal",
                chat_path="/test/chat.json",
            )

            assert action.action == "print"
            assert chat_data["messages"] == []
            mock_save.assert_awaited_once_with(
                force=True,
                chat_path="/test/chat.json",
                chat_data=chat_data,
            )

    @pytest.mark.asyncio
    async def test_handle_user_cancel_retry_mode_does_not_save(self, orchestrator):
        chat_data = {"metadata": {}, "messages": []}

        with patch.object(orchestrator.manager, "save_current_chat", new_callable=AsyncMock) as mock_save:
            action = await orchestrator.handle_user_cancel(chat_data, "retry")

            assert action.action == "print"
            mock_save.assert_not_called()
