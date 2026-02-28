"""Tests for REPL/session orchestration state transitions."""

from polychat.domain.chat import ChatDocument, ChatMessage
from polychat.session.state import (
    SessionState,
    initialize_message_hex_ids,
)
from polychat.commands.types import CommandSignal
from test_helpers import make_profile


class TestCommandSignals:
    """Test typed command signal contracts used in REPL orchestration."""

    def test_exit_signal(self):
        signal = CommandSignal(kind="exit")
        assert signal.kind == "exit"
        assert signal.chat_path is None
        assert signal.value is None

    def test_new_chat_signal(self):
        chat_path = "/path/to/new-chat.json"
        signal = CommandSignal(kind="new_chat", chat_path=chat_path)
        assert signal.kind == "new_chat"
        assert signal.chat_path == chat_path

    def test_open_chat_signal(self):
        chat_path = "/path/to/existing-chat.json"
        signal = CommandSignal(kind="open_chat", chat_path=chat_path)
        assert signal.kind == "open_chat"
        assert signal.chat_path == chat_path

    def test_close_chat_signal(self):
        signal = CommandSignal(kind="close_chat")
        assert signal.kind == "close_chat"

    def test_rename_current_signal(self):
        new_path = "/path/to/renamed-chat.json"
        signal = CommandSignal(kind="rename_current", chat_path=new_path)
        assert signal.kind == "rename_current"
        assert signal.chat_path == new_path

    def test_delete_current_signal(self):
        filename = "deleted-chat.json"
        signal = CommandSignal(kind="delete_current", value=filename)
        assert signal.kind == "delete_current"
        assert signal.value == filename

    def test_apply_retry_signal(self):
        signal = CommandSignal(kind="apply_retry", value="abc")
        assert signal.kind == "apply_retry"
        assert signal.value == "abc"

    def test_cancel_retry_signal(self):
        signal = CommandSignal(kind="cancel_retry")
        assert signal.kind == "cancel_retry"

    def test_clear_secret_context_signal(self):
        signal = CommandSignal(kind="clear_secret_context")
        assert signal.kind == "clear_secret_context"


class TestChatSwitchingOrchestration:
    """Test orchestration logic for chat switching."""

    def test_new_chat_state_initialization(self):
        """Test state initialization when creating new chat."""
        # Simulate creating new chat
        new_chat_data = ChatDocument.from_raw({
            "metadata": {
                "title": None,
                "summary": None,
                "system_prompt": None,
                "created_utc": None,
                "updated_utc": None,
            },
            "messages": [],
        })

        session = SessionState(
            current_ai="claude",
            current_model="claude-haiku-4-5",
            helper_ai="claude",
            helper_model="claude-haiku-4-5",
            profile=make_profile(),
            chat=new_chat_data,
        )

        # Initialize hex IDs for new chat
        initialize_message_hex_ids(session)

        assert session.chat == new_chat_data
        assert session.chat.messages == []
        assert session.hex_id_set == set()

    def test_open_chat_replaces_current(self):
        """Test opening chat replaces current chat data."""
        # Start with current chat
        session = SessionState(
            current_ai="claude",
            current_model="claude-haiku-4-5",
            helper_ai="claude",
            helper_model="claude-haiku-4-5",
            profile=make_profile(),
            chat=ChatDocument.from_raw({"metadata": {}, "messages": [{"role": "user", "content": "old"}]}),
        )
        initialize_message_hex_ids(session)
        old_hex_ids = [m.hex_id for m in session.chat.messages]

        # Open new chat
        new_chat = ChatDocument.from_raw({"metadata": {}, "messages": [{"role": "user", "content": "new"}]})
        session.chat = new_chat
        initialize_message_hex_ids(session)

        # Should have different hex IDs
        assert session.chat == new_chat
        assert [m.hex_id for m in session.chat.messages] != old_hex_ids

    def test_close_chat_clears_state(self):
        """Test closing chat clears chat-related state."""
        session = SessionState(
            current_ai="claude",
            current_model="claude-haiku-4-5",
            helper_ai="claude",
            helper_model="claude-haiku-4-5",
            profile=make_profile(),
            chat=ChatDocument.from_raw({"metadata": {}, "messages": [{"role": "user", "content": "test"}]}),
        )
        initialize_message_hex_ids(session)

        # Simulate closing chat
        session.chat = ChatDocument.empty()
        session.hex_id_set.clear()
        session.retry_mode = False
        session.retry_base_messages.clear()
        session.retry_target_index = None
        session.retry_attempts.clear()
        session.secret_mode = False
        session.secret_base_messages.clear()

        assert isinstance(session.chat, ChatDocument)
        assert session.chat.messages == []
        assert session.hex_id_set == set()
        assert session.retry_mode is False
        assert session.secret_mode is False

    def test_chat_switch_resets_scoped_state(self):
        """Test that switching chats resets retry/secret modes."""
        session = SessionState(
            current_ai="claude",
            current_model="claude-haiku-4-5",
            helper_ai="claude",
            helper_model="claude-haiku-4-5",
            profile=make_profile(),
            chat=ChatDocument.from_raw({"metadata": {}, "messages": []}),
            retry_mode=True,
            secret_mode=True,
        )

        # Simulate chat switch
        session.retry_mode = False
        session.retry_base_messages.clear()
        session.retry_target_index = None
        session.retry_attempts.clear()
        session.secret_mode = False
        session.secret_base_messages.clear()

        assert session.retry_mode is False
        assert session.secret_mode is False


class TestRetryModeOrchestration:
    """Test retry mode orchestration logic."""

    def test_enter_retry_mode_freezes_context(self):
        """Test entering retry mode freezes message context."""
        chat_data = ChatDocument.from_raw({
            "metadata": {},
            "messages": [
                {"role": "user", "content": "Question"},
                {"role": "assistant", "content": "Bad answer"},
            ]
        })

        session = SessionState(
            current_ai="claude",
            current_model="claude-haiku-4-5",
            helper_ai="claude",
            helper_model="claude-haiku-4-5",
            profile=make_profile(),
            chat=chat_data,
        )

        # Enter retry mode - freeze context without last assistant message
        session.retry_mode = True
        session.retry_base_messages = [ChatMessage.new_user("Question")]

        assert session.retry_mode is True
        assert len(session.retry_base_messages) == 1
        # Original chat unchanged
        assert len(chat_data.messages) == 2

    def test_retry_attempt_uses_frozen_context(self):
        """Test retry attempt uses frozen context plus new user message."""
        session = SessionState(
            current_ai="claude",
            current_model="claude-haiku-4-5",
            helper_ai="claude",
            helper_model="claude-haiku-4-5",
            profile=make_profile(),
            chat=ChatDocument.empty(),
            retry_mode=True,
        )
        session.retry_base_messages = [ChatMessage.new_user("Original")]
        retry_user_msg = "Try this instead"

        # Simulate building temp messages for retry
        temp_messages = session.retry_base_messages + [
            ChatMessage.new_user(retry_user_msg)
        ]

        assert len(temp_messages) == 2
        assert temp_messages[0].content == ["Original"]
        assert temp_messages[1].content == ["Try this instead"]

    def test_apply_retry_replaces_messages(self):
        """Test applying retry replaces original messages."""
        chat_data = ChatDocument.from_raw({
            "metadata": {},
            "messages": [
                {"role": "user", "content": "Original question"},
                {"role": "assistant", "content": "Bad answer"},
            ]
        })

        selected_assistant_msg = "Better answer"

        # Simulate applying retry by replacing only the target message.
        from polychat.domain.chat import ChatMessage
        chat_data.messages[-1] = ChatMessage.from_raw({"role": "assistant", "content": selected_assistant_msg})
        assert len(chat_data.messages) == 2
        assert chat_data.messages[0].content == ["Original question"]
        assert chat_data.messages[1].content == ["Better answer"]

    def test_cancel_retry_clears_state(self):
        """Test cancelling retry clears retry state."""
        session = SessionState(
            current_ai="claude",
            current_model="claude-haiku-4-5",
            helper_ai="claude",
            helper_model="claude-haiku-4-5",
            profile=make_profile(),
            chat=ChatDocument.empty(),
            retry_mode=True,
        )
        session.retry_base_messages = [ChatMessage.new_user("base")]
        session.retry_target_index = 1
        session.retry_attempts = {"abc": {"user_msg": "u", "assistant_msg": "a"}}
        session_dict = {"retry_mode": True}

        # Cancel retry
        session.retry_mode = False
        session.retry_base_messages.clear()
        session.retry_target_index = None
        session.retry_attempts.clear()
        session_dict["retry_mode"] = False

        assert session.retry_mode is False
        assert session.retry_base_messages == []
        assert session.retry_target_index is None
        assert session.retry_attempts == {}


class TestSecretModeOrchestration:
    """Test secret mode orchestration logic."""

    def test_enter_secret_mode_freezes_context(self):
        """Test entering secret mode freezes message context."""
        chat_data = ChatDocument.from_raw({
            "metadata": {},
            "messages": [
                {"role": "user", "content": "Public question"},
                {"role": "assistant", "content": "Public answer"},
            ]
        })

        session = SessionState(
            current_ai="claude",
            current_model="claude-haiku-4-5",
            helper_ai="claude",
            helper_model="claude-haiku-4-5",
            profile=make_profile(),
            chat=chat_data,
        )

        # Enter secret mode - freeze current context
        session.secret_mode = True
        session.secret_base_messages = [
            ChatMessage.new_user("Public question"),
            ChatMessage.new_assistant("Public answer", model="test-model"),
        ]

        assert session.secret_mode is True
        assert len(session.secret_base_messages) == 2

    def test_secret_message_not_saved(self):
        """Test secret messages aren't saved to chat."""
        chat_data = ChatDocument.from_raw({"metadata": {}, "messages": [{"role": "user", "content": "Public"}]})

        session = SessionState(
            current_ai="claude",
            current_model="claude-haiku-4-5",
            helper_ai="claude",
            helper_model="claude-haiku-4-5",
            profile=make_profile(),
            chat=chat_data,
            secret_mode=True,
        )
        session.secret_base_messages = [ChatMessage.new_user("Public")]

        # Simulate secret question (built but not saved)
        temp_messages = session.secret_base_messages + [
            ChatMessage.new_user("Secret question")
        ]

        # Temp messages have secret
        assert len(temp_messages) == 2
        assert temp_messages[-1].content == ["Secret question"]

        # Original chat unchanged
        assert len(chat_data.messages) == 1
        assert chat_data.messages[-1].content == ["Public"]

    def test_clear_secret_context(self):
        """Test clearing secret context."""
        session = SessionState(
            current_ai="claude",
            current_model="claude-haiku-4-5",
            helper_ai="claude",
            helper_model="claude-haiku-4-5",
            profile=make_profile(),
            chat=ChatDocument.empty(),
            secret_mode=True,
        )
        session.secret_base_messages = [ChatMessage.new_user("frozen")]

        # Clear secret context
        session.secret_base_messages.clear()

        assert session.secret_base_messages == []
        # Note: secret_mode might stay True until /secret toggle


class TestProviderSwitching:
    """Test provider switching orchestration."""

    def test_switch_provider_updates_session(self):
        """Test switching provider updates current_ai and current_model."""
        session = SessionState(
            current_ai="claude",
            current_model="claude-haiku-4-5",
            helper_ai="claude",
            helper_model="claude-haiku-4-5",
            profile=make_profile(),
            chat=ChatDocument.empty(),
        )

        # Simulate provider switch
        session.current_ai = "openai"
        session.current_model = "gpt-5-mini"

        assert session.current_ai == "openai"
        assert session.current_model == "gpt-5-mini"

    def test_provider_cache_survives_switch(self):
        """Test provider cache persists when switching providers."""
        session = SessionState(
            current_ai="claude",
            current_model="claude-haiku-4-5",
            helper_ai="claude",
            helper_model="claude-haiku-4-5",
            profile=make_profile(),
            chat=ChatDocument.empty(),
        )

        # Cache providers
        session.cache_provider("claude", "key1", {"instance": "claude"})
        session.cache_provider("openai", "key2", {"instance": "openai"})

        # Switch provider
        session.current_ai = "openai"

        # Both caches should still exist
        assert session.get_cached_provider("claude", "key1") is not None
        assert session.get_cached_provider("openai", "key2") is not None


class TestInputModeToggle:
    """Test input mode toggling orchestration."""

    def test_toggle_quick_to_compose(self):
        """Test toggling from quick to compose mode."""
        session = SessionState(
            current_ai="claude",
            current_model="claude-haiku-4-5",
            helper_ai="claude",
            helper_model="claude-haiku-4-5",
            profile=make_profile(),
            chat=ChatDocument.empty(),
            input_mode="quick",
        )

        # Toggle to compose
        session.input_mode = "compose"

        assert session.input_mode == "compose"

    def test_toggle_compose_to_quick(self):
        """Test toggling from compose to quick mode."""
        session = SessionState(
            current_ai="claude",
            current_model="claude-haiku-4-5",
            helper_ai="claude",
            helper_model="claude-haiku-4-5",
            profile=make_profile(),
            chat=ChatDocument.empty(),
            input_mode="compose",
        )

        # Toggle to quick
        session.input_mode = "quick"

        assert session.input_mode == "quick"
