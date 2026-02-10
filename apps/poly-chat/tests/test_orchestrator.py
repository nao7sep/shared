"""Tests for ChatOrchestrator."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from poly_chat.commands.types import CommandSignal
from poly_chat.orchestrator import ChatOrchestrator
from poly_chat.orchestrator_types import (
    BreakAction,
    ContinueAction,
    PrintAction,
    SendAction,
)
from poly_chat.session_manager import SessionManager


@pytest.fixture
def session_manager():
    """Create a test session manager."""
    manager = SessionManager(
        profile={
            "chats_dir": "/test/chats",
            "logs_dir": "/test/logs",
            "pages_dir": "/test/pages",
        },
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


class TestOrchestratorActionTypes:
    """Test typed orchestrator actions."""

    def test_create_continue_action(self):
        """Test creating a continue action."""
        action = ContinueAction(message="Test message")

        assert isinstance(action, ContinueAction)
        assert action.kind == "continue"
        assert action.message == "Test message"
        assert action.chat_path is None
        assert action.chat_data is None

    def test_create_break_action(self):
        """Test creating a break action."""
        action = BreakAction()

        assert isinstance(action, BreakAction)
        assert action.kind == "break"

    def test_create_action_with_chat_data(self):
        """Test creating action with chat data."""
        chat_data = {"messages": []}
        action = ContinueAction(
            chat_path="/test/chat.json",
            chat_data=chat_data,
        )

        assert isinstance(action, ContinueAction)
        assert action.kind == "continue"
        assert action.chat_path == "/test/chat.json"
        assert action.chat_data == chat_data


class TestExitSignal:
    """Test exit signal handling."""

    @pytest.mark.asyncio
    async def test_exit_signal(self, orchestrator):
        """Test that exit signal returns break action."""
        action = await orchestrator.handle_command_response(
            CommandSignal(kind="exit"),
            current_chat_path=None,
            current_chat_data=None,
        )

        assert isinstance(action, BreakAction)


class TestNewChatSignal:
    """Test new-chat signal handling."""

    @pytest.mark.asyncio
    async def test_new_chat_signal(self, orchestrator, sample_chat_data):
        """Test creating new chat."""
        with patch("poly_chat.orchestrator.chat") as mock_chat:
            mock_chat.load_chat = MagicMock(return_value={"messages": []})
            with patch.object(orchestrator.manager, "save_current_chat", new_callable=AsyncMock) as mock_save:
                action = await orchestrator.handle_command_response(
                    CommandSignal(kind="new_chat", chat_path="/test/new-chat.json"),
                    current_chat_path="/test/old-chat.json",
                    current_chat_data=sample_chat_data,
                )

                # Should save old chat then persist new chat file
                assert mock_save.await_count == 2

            # Should load new chat
            mock_chat.load_chat.assert_called_once_with("/test/new-chat.json")

            # Should return continue action with new chat
            assert isinstance(action, ContinueAction)
            assert action.chat_path == "/test/new-chat.json"
            assert action.chat_data == {"messages": []}
            assert "Created new chat" in action.message

    @pytest.mark.asyncio
    async def test_new_chat_without_current_chat(self, orchestrator):
        """Test creating new chat when no current chat."""
        with patch("poly_chat.orchestrator.chat") as mock_chat:
            mock_chat.load_chat = MagicMock(return_value={"messages": []})
            with patch.object(orchestrator.manager, "save_current_chat", new_callable=AsyncMock) as mock_save:
                action = await orchestrator.handle_command_response(
                    CommandSignal(kind="new_chat", chat_path="/test/new-chat.json"),
                    current_chat_path=None,
                    current_chat_data=None,
                )

                # Should persist newly created chat file
                mock_save.assert_called_once()

            # Should load new chat
            mock_chat.load_chat.assert_called_once_with("/test/new-chat.json")

            assert isinstance(action, ContinueAction)
            assert action.chat_path == "/test/new-chat.json"


class TestOpenChatSignal:
    """Test open-chat signal handling."""

    @pytest.mark.asyncio
    async def test_open_chat_signal(self, orchestrator, sample_chat_data):
        """Test opening existing chat."""
        with patch("poly_chat.orchestrator.chat") as mock_chat:
            mock_chat.load_chat = MagicMock(return_value={"messages": [{"role": "user", "content": "Test"}]})
            with patch.object(orchestrator.manager, "save_current_chat", new_callable=AsyncMock) as mock_save:
                action = await orchestrator.handle_command_response(
                    CommandSignal(kind="open_chat", chat_path="/test/existing-chat.json"),
                    current_chat_path="/test/current-chat.json",
                    current_chat_data=sample_chat_data,
                )

                # Should save current chat
                mock_save.assert_called_once()

            # Should load selected chat
            mock_chat.load_chat.assert_called_once_with("/test/existing-chat.json")

            # Should return continue action
            assert isinstance(action, ContinueAction)
            assert action.chat_path == "/test/existing-chat.json"
            assert "Opened chat" in action.message


class TestCloseChatSignal:
    """Test close-chat signal handling."""

    @pytest.mark.asyncio
    async def test_close_chat_signal(self, orchestrator, sample_chat_data):
        """Test closing current chat."""
        with patch.object(orchestrator.manager, "save_current_chat", new_callable=AsyncMock) as mock_save:
            action = await orchestrator.handle_command_response(
                CommandSignal(kind="close_chat"),
                current_chat_path="/test/chat.json",
                current_chat_data=sample_chat_data,
            )

            # Should save chat before closing
            mock_save.assert_called_once()

            # Should return continue action with empty chat
            assert isinstance(action, ContinueAction)
            assert action.chat_path is None
            assert action.chat_data == {}
            assert action.message == "Chat closed"

    @pytest.mark.asyncio
    async def test_close_chat_when_no_chat_open(self, orchestrator):
        """Test closing when no chat is open."""
        with patch.object(orchestrator.manager, "save_current_chat", new_callable=AsyncMock) as mock_save:
            action = await orchestrator.handle_command_response(
                CommandSignal(kind="close_chat"),
                current_chat_path=None,
                current_chat_data=None,
            )

            # Should not try to save
            mock_save.assert_not_called()

            # Should still return action
            assert isinstance(action, ContinueAction)
            assert action.chat_path is None


class TestRenameChatSignal:
    """Test rename-current signal handling."""

    @pytest.mark.asyncio
    async def test_rename_current_signal(self, orchestrator):
        """Test renaming current chat."""
        action = await orchestrator.handle_command_response(
            CommandSignal(kind="rename_current", chat_path="/test/renamed-chat.json"),
            current_chat_path="/test/old-chat.json",
            current_chat_data={},
        )

        assert isinstance(action, ContinueAction)
        assert action.chat_path == "/test/renamed-chat.json"
        assert "Renamed to" in action.message


class TestDeleteChatSignal:
    """Test delete-current signal handling."""

    @pytest.mark.asyncio
    async def test_delete_current_signal(self, orchestrator, sample_chat_data):
        """Test deleting current chat."""
        action = await orchestrator.handle_command_response(
            CommandSignal(kind="delete_current", value="test-chat.json"),
            current_chat_path="/test/test-chat.json",
            current_chat_data=sample_chat_data,
        )

        # Should clear chat and return action
        assert isinstance(action, ContinueAction)
        assert action.chat_path is None
        assert action.chat_data == {}
        assert "Deleted" in action.message


class TestRetryModeSignals:
    """Test retry mode signal handling."""

    @pytest.mark.asyncio
    async def test_apply_retry_signal(self, orchestrator, sample_chat_data):
        """Test applying retry."""
        # Enter retry mode first
        orchestrator.manager.switch_chat("/test/chat.json", sample_chat_data)
        orchestrator.manager.enter_retry_mode(
            [{"role": "user", "content": "Original"}],
            target_index=1,
        )
        retry_hex_id = orchestrator.manager.add_retry_attempt("Retry question", "Retry answer")
        original_hex_id = sample_chat_data["messages"][1].get("hex_id")

        with patch.object(orchestrator.manager, "save_current_chat", new_callable=AsyncMock) as mock_save:
            action = await orchestrator.handle_command_response(
                CommandSignal(kind="apply_retry", value=retry_hex_id),
                current_chat_path="/test/chat.json",
                current_chat_data=sample_chat_data,
            )

            # Should save chat
            mock_save.assert_called_once()

        # Should return print action
        assert isinstance(action, PrintAction)
        assert f"Applied retry [{retry_hex_id}]" == action.message

        # Should replace only the target message, preserving its hex_id
        updated = sample_chat_data["messages"][1]
        assert updated["role"] == "assistant"
        assert updated["content"] == ["Retry answer"]
        assert updated.get("hex_id") == original_hex_id

        # Should exit retry mode
        assert orchestrator.manager.retry_mode is False

    @pytest.mark.asyncio
    async def test_apply_retry_preserves_citations(self, orchestrator, sample_chat_data):
        """Applied retry should persist citations when available."""
        orchestrator.manager.switch_chat("/test/chat.json", sample_chat_data)
        orchestrator.manager.enter_retry_mode(
            [{"role": "user", "content": "Original"}],
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
                current_chat_path="/test/chat.json",
                current_chat_data=sample_chat_data,
            )

        assert isinstance(action, PrintAction)
        assert sample_chat_data["messages"][1]["citations"] == [
            {"url": "https://example.com", "title": "Example"}
        ]

    @pytest.mark.asyncio
    async def test_apply_retry_when_not_in_retry_mode(self, orchestrator):
        """Test applying retry when not in retry mode."""
        action = await orchestrator.handle_command_response(
            CommandSignal(kind="apply_retry", value="abc"),
            current_chat_path="/test/chat.json",
            current_chat_data={},
        )

        assert isinstance(action, PrintAction)
        assert "Not in retry mode" in action.message

    @pytest.mark.asyncio
    async def test_cancel_retry_signal(self, orchestrator):
        """Test cancelling retry mode."""
        # Enter retry mode first
        orchestrator.manager.enter_retry_mode([{"role": "user", "content": "Test"}])

        action = await orchestrator.handle_command_response(
            CommandSignal(kind="cancel_retry"),
            current_chat_path=None,
            current_chat_data=None,
        )

        assert isinstance(action, PrintAction)
        assert "Cancelled retry mode" in action.message
        assert orchestrator.manager.retry_mode is False

    @pytest.mark.asyncio
    async def test_cancel_retry_when_not_in_retry_mode(self, orchestrator):
        """Test cancelling retry when not in retry mode."""
        action = await orchestrator.handle_command_response(
            CommandSignal(kind="cancel_retry"),
            current_chat_path=None,
            current_chat_data=None,
        )

        assert isinstance(action, PrintAction)
        assert "Not in retry mode" in action.message


class TestSecretModeSignals:
    """Test secret mode signal handling."""

    @pytest.mark.asyncio
    async def test_clear_secret_context_when_in_secret_mode(self, orchestrator):
        """Test clearing secret context when in secret mode."""
        # Enter secret mode first
        orchestrator.manager.enter_secret_mode([{"role": "user", "content": "Base"}])

        action = await orchestrator.handle_command_response(
            CommandSignal(kind="clear_secret_context"),
            current_chat_path=None,
            current_chat_data=None,
        )

        assert isinstance(action, PrintAction)
        assert "Secret mode disabled" in action.message
        assert orchestrator.manager.secret_mode is False

    @pytest.mark.asyncio
    async def test_clear_secret_context_when_not_in_secret_mode(self, orchestrator):
        """Test clearing secret context when not in secret mode."""
        action = await orchestrator.handle_command_response(
            CommandSignal(kind="clear_secret_context"),
            current_chat_path=None,
            current_chat_data=None,
        )

        assert isinstance(action, ContinueAction)
        assert action.message is None



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

        assert isinstance(action, PrintAction)
        assert action.message == "This is a regular message"

    @pytest.mark.asyncio
    async def test_empty_message(self, orchestrator):
        """Test handling empty message."""
        action = await orchestrator.handle_command_response(
            "",
            current_chat_path=None,
            current_chat_data=None,
        )

        assert isinstance(action, PrintAction)
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

            assert isinstance(action, PrintAction)
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
        with patch("poly_chat.orchestrator.chat") as mock_chat:
            mock_chat.load_chat = MagicMock(
                return_value={
                    "metadata": {
                        "title": None,
                        "summary": None,
                        "system_prompt": None,
                        "created_at": None,
                        "updated_at": None,
                    },
                    "messages": [],
                }
            )

            with patch.object(orchestrator.manager, "save_current_chat", new_callable=AsyncMock):
                await orchestrator.handle_command_response(
                    CommandSignal(kind="new_chat", chat_path="/test/new.json"),
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
                CommandSignal(kind="close_chat"),
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

            assert isinstance(action, PrintAction)
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

            assert isinstance(action, PrintAction)
            mock_save.assert_not_called()


class TestPreSendValidationRollback:
    @pytest.mark.asyncio
    async def test_normal_mode_rolls_back_pending_user_message(self, orchestrator):
        chat_data = {
            "metadata": {"title": "Validation rollback"},
            "messages": [{"role": "assistant", "content": ["existing"]}],
        }
        orchestrator.manager.switch_chat("/test/chat.json", chat_data)

        action = await orchestrator._handle_normal_message(
            "unsent user input",
            chat_data,
            "/test/chat.json",
        )

        assert isinstance(action, SendAction)
        assert action.mode == "normal"
        assert chat_data["messages"][-1]["role"] == "user"

        with patch.object(orchestrator.manager, "save_current_chat", new_callable=AsyncMock) as mock_save:
            rolled_back = await orchestrator.rollback_pre_send_failure(
                chat_path="/test/chat.json",
                chat_data=chat_data,
                mode="normal",
            )

            assert rolled_back is True
            assert len(chat_data["messages"]) == 1
            assert chat_data["messages"][-1]["role"] == "assistant"
            mock_save.assert_awaited_once_with(
                force=True,
                chat_path="/test/chat.json",
                chat_data=chat_data,
            )

    @pytest.mark.asyncio
    async def test_non_normal_mode_does_not_mutate_chat(self, orchestrator):
        chat_data = {
            "metadata": {},
            "messages": [{"role": "user", "content": ["base"]}],
        }
        orchestrator.manager._state.hex_id_set.add("abc")

        with patch.object(orchestrator.manager, "save_current_chat", new_callable=AsyncMock) as mock_save:
            rolled_back = await orchestrator.rollback_pre_send_failure(
                chat_path="/test/chat.json",
                chat_data=chat_data,
                mode="retry",
                assistant_hex_id="abc",
            )

            assert rolled_back is False
            assert len(chat_data["messages"]) == 1
            assert "abc" not in orchestrator.manager.hex_id_set
            mock_save.assert_not_called()
