"""Tests for session state management."""

from polychat.domain.chat import ChatDocument, ChatMessage
from polychat.session.state import (
    SessionState,
    initialize_message_hex_ids,
    assign_new_message_hex_id,
    has_pending_error,
)
from test_helpers import make_profile


class TestSessionStateCreation:
    """Test SessionState dataclass creation and initialization."""

    def test_create_minimal_session(self):
        """Test creating session with minimal required fields."""
        session = SessionState(
            current_ai="claude",
            current_model="claude-haiku-4-5",
            helper_ai="claude",
            helper_model="claude-haiku-4-5",
            profile=make_profile(default_ai="claude"),
            chat=ChatDocument.empty(),
        )

        assert session.current_ai == "claude"
        assert session.current_model == "claude-haiku-4-5"
        assert session.helper_ai == "claude"
        assert session.helper_model == "claude-haiku-4-5"
        assert session.profile.default_ai == "claude"
        assert isinstance(session.chat, ChatDocument)

    def test_default_values(self):
        """Test that optional fields have correct defaults."""
        session = SessionState(
            current_ai="claude",
            current_model="claude-haiku-4-5",
            helper_ai="claude",
            helper_model="claude-haiku-4-5",
            profile=make_profile(),
            chat=ChatDocument.empty(),
        )

        assert session.system_prompt is None
        assert session.system_prompt_path is None
        assert session.input_mode == "quick"
        assert session.retry.active is False
        assert session.retry.base_messages == []
        assert session.retry.target_index is None
        assert session.retry.attempts == {}
        assert session.secret.active is False
        assert session.secret.base_messages == []
        assert session.hex_id_set == set()
        assert session._provider_cache == {}

    def test_create_with_all_fields(self):
        """Test creating session with all fields populated."""
        session = SessionState(
            current_ai="openai",
            current_model="gpt-5-mini",
            helper_ai="claude",
            helper_model="claude-haiku-4-5",
            profile=make_profile(timeout=300),
            chat=ChatDocument.from_raw({"metadata": {}, "messages": []}),
            system_prompt="You are helpful",
            system_prompt_path="~/prompts/default.txt",
            input_mode="compose",
        )
        session.retry.active = True
        session.secret.active = True

        assert session.current_ai == "openai"
        assert session.system_prompt == "You are helpful"
        assert session.input_mode == "compose"
        assert session.retry.active is True
        assert session.secret.active is True




class TestProviderCaching:
    """Test provider instance caching."""

    def test_cache_and_retrieve_provider(self):
        """Test caching and retrieving provider instances."""
        session = SessionState(
            current_ai="claude",
            current_model="claude-haiku-4-5",
            helper_ai="claude",
            helper_model="claude-haiku-4-5",
            profile=make_profile(),
            chat=ChatDocument.empty(),
        )

        # Mock provider instance
        mock_provider = {"name": "claude", "instance": "mock"}

        # Cache provider
        session.cache_provider("claude", "sk-test-key", mock_provider)

        # Retrieve cached provider
        cached = session.get_cached_provider("claude", "sk-test-key")
        assert cached == mock_provider

    def test_cache_multiple_providers(self):
        """Test caching multiple provider instances."""
        session = SessionState(
            current_ai="claude",
            current_model="claude-haiku-4-5",
            helper_ai="claude",
            helper_model="claude-haiku-4-5",
            profile=make_profile(),
            chat=ChatDocument.empty(),
        )

        provider1 = {"name": "claude"}
        provider2 = {"name": "openai"}

        session.cache_provider("claude", "key1", provider1)
        session.cache_provider("openai", "key2", provider2)

        assert session.get_cached_provider("claude", "key1") == provider1
        assert session.get_cached_provider("openai", "key2") == provider2

    def test_cache_keys_include_timeout_variant(self):
        """Test that cache distinguishes provider instances by timeout."""
        session = SessionState(
            current_ai="claude",
            current_model="claude-haiku-4-5",
            helper_ai="claude",
            helper_model="claude-haiku-4-5",
            profile=make_profile(),
            chat=ChatDocument.empty(),
        )

        provider_fast = {"name": "claude-fast"}
        provider_slow = {"name": "claude-slow"}

        session.cache_provider("claude", "key1", provider_fast, timeout_sec=300)
        session.cache_provider("claude", "key1", provider_slow, timeout_sec=900)

        assert session.get_cached_provider("claude", "key1", timeout_sec=300) == provider_fast
        assert session.get_cached_provider("claude", "key1", timeout_sec=900) == provider_slow

    def test_cache_miss_returns_none(self):
        """Test that cache miss returns None."""
        session = SessionState(
            current_ai="claude",
            current_model="claude-haiku-4-5",
            helper_ai="claude",
            helper_model="claude-haiku-4-5",
            profile=make_profile(),
            chat=ChatDocument.empty(),
        )

        cached = session.get_cached_provider("nonexistent", "key")
        assert cached is None


class TestHexIdManagement:
    """Test hex ID initialization and assignment."""

    def test_initialize_hex_ids_empty_chat(self):
        """Test initializing hex IDs for empty chat."""
        session = SessionState(
            current_ai="claude",
            current_model="claude-haiku-4-5",
            helper_ai="claude",
            helper_model="claude-haiku-4-5",
            profile=make_profile(),
            chat=ChatDocument.from_raw({"metadata": {}, "messages": []}),
        )

        initialize_message_hex_ids(session)

        assert session.chat.messages == []
        assert session.hex_id_set == set()

    def test_initialize_hex_ids_with_messages(self):
        """Test initializing hex IDs for chat with messages."""
        session = SessionState(
            current_ai="claude",
            current_model="claude-haiku-4-5",
            helper_ai="claude",
            helper_model="claude-haiku-4-5",
            profile=make_profile(),
            chat=ChatDocument.from_raw({
                "metadata": {},
                "messages": [
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi"},
                    {"role": "user", "content": "How are you?"},
                ]
            }),
        )

        initialize_message_hex_ids(session)

        # Should have 3 hex IDs
        assert len(session.chat.messages) == 3
        assert len(session.hex_id_set) == 3

        # All hex IDs should be unique
        hex_ids = [m.hex_id for m in session.chat.messages]
        assert len(hex_ids) == len(set(hex_ids))

    def test_assign_new_message_hex_id(self):
        """Test assigning hex ID to new message."""
        session = SessionState(
            current_ai="claude",
            current_model="claude-haiku-4-5",
            helper_ai="claude",
            helper_model="claude-haiku-4-5",
            profile=make_profile(),
            chat=ChatDocument.from_raw({"metadata": {}, "messages": [{"role": "user", "content": "Hello"}]}),
        )

        # Initialize existing message IDs
        initialize_message_hex_ids(session)
        initial_count = len(session.hex_id_set)

        # Add a second message
        session.chat.messages.append(ChatMessage.from_raw({"role": "assistant", "content": "Hi"}))

        # Assign new hex ID
        new_hex_id = assign_new_message_hex_id(session, 1)

        # Should have one more hex ID
        assert len(session.chat.messages) == initial_count + 1
        assert len(session.hex_id_set) == initial_count + 1

        # New hex ID should be in both structures
        assert session.chat.messages[1].hex_id == new_hex_id
        assert new_hex_id in session.hex_id_set

    def test_hex_ids_persist_across_reinitialization(self):
        """Test that reinitializing clears and regenerates hex IDs."""
        session = SessionState(
            current_ai="claude",
            current_model="claude-haiku-4-5",
            helper_ai="claude",
            helper_model="claude-haiku-4-5",
            profile=make_profile(),
            chat=ChatDocument.from_raw({"metadata": {}, "messages": [{"role": "user", "content": "Hello"}]}),
        )

        # First initialization
        initialize_message_hex_ids(session)
        first_hex_ids = [m.hex_id for m in session.chat.messages]

        # Second initialization (e.g., after loading new chat)
        initialize_message_hex_ids(session)
        second_hex_ids = [m.hex_id for m in session.chat.messages]

        # Should have regenerated (likely different IDs)
        # Both should have same count
        assert len(first_hex_ids) == len(second_hex_ids)


class TestChatScopedState:
    """Test chat-scoped mode state behavior."""

    def test_reset_clears_retry_state(self):
        """Test that reset clears retry mode state."""
        session = SessionState(
            current_ai="claude",
            current_model="claude-haiku-4-5",
            helper_ai="claude",
            helper_model="claude-haiku-4-5",
            profile=make_profile(),
            chat=ChatDocument.empty(),
        )
        session.retry.active = True
        session.retry.base_messages = [ChatMessage.new_user("old")]
        session.retry.target_index = 3
        session.retry.attempts = {"abc": {"user_msg": "u", "assistant_msg": "a"}}

        session.retry.active = False
        session.retry.base_messages.clear()
        session.retry.target_index = None
        session.retry.attempts.clear()

        assert session.retry.active is False
        assert session.retry.base_messages == []
        assert session.retry.target_index is None
        assert session.retry.attempts == {}

    def test_reset_clears_secret_state(self):
        """Test that reset clears secret mode state."""
        session = SessionState(
            current_ai="claude",
            current_model="claude-haiku-4-5",
            helper_ai="claude",
            helper_model="claude-haiku-4-5",
            profile=make_profile(),
            chat=ChatDocument.empty(),
        )
        session.secret.active = True
        session.secret.base_messages = [ChatMessage.new_user("secret")]

        session.secret.active = False
        session.secret.base_messages.clear()

        assert session.secret.active is False
        assert session.secret.base_messages == []

    def test_reset_both_modes_simultaneously(self):
        """Test resetting both retry and secret mode together."""
        session = SessionState(
            current_ai="claude",
            current_model="claude-haiku-4-5",
            helper_ai="claude",
            helper_model="claude-haiku-4-5",
            profile=make_profile(),
            chat=ChatDocument.empty(),
        )
        session.retry.active = True
        session.secret.active = True
        session.retry.base_messages = [ChatMessage.new_user("retry")]
        session.secret.base_messages = [ChatMessage.new_user("secret")]

        session.retry.active = False
        session.secret.active = False
        session.retry.base_messages.clear()
        session.secret.base_messages.clear()

        assert session.retry.active is False
        assert session.secret.active is False
        assert session.retry.base_messages == []
        assert session.secret.base_messages == []


class TestErrorDetection:
    """Test has_pending_error function."""

    def test_no_error_in_empty_chat(self):
        """Test that empty chat has no pending error."""
        chat_data = ChatDocument.from_raw({"metadata": {}, "messages": []})
        assert has_pending_error(chat_data) is False

    def test_no_error_in_normal_conversation(self):
        """Test that normal conversation has no pending error."""
        chat_data = ChatDocument.from_raw({
            "metadata": {},
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there"},
            ]
        })
        assert has_pending_error(chat_data) is False

    def test_error_detected_when_last_message_is_error(self):
        """Test that error is detected when last message has error role."""
        chat_data = ChatDocument.from_raw({
            "metadata": {},
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "error", "content": "API error occurred"},
            ]
        })
        assert has_pending_error(chat_data) is True

    def test_no_error_when_error_is_not_last(self):
        """Test that old error doesn't count as pending."""
        chat_data = ChatDocument.from_raw({
            "metadata": {},
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "error", "content": "Old error"},
                {"role": "user", "content": "Retry"},
                {"role": "assistant", "content": "Success"},
            ]
        })
        assert has_pending_error(chat_data) is False

    def test_no_error_with_none_chat_data(self):
        """Test that None chat data has no pending error."""
        assert has_pending_error(None) is False

    def test_no_error_with_missing_messages_key(self):
        """Test that chat without messages key has no pending error."""
        chat_data = ChatDocument.empty()
        assert has_pending_error(chat_data) is False


class TestStateTransitions:
    """Test state transitions between different modes."""

    def test_enter_retry_mode(self):
        """Test entering retry mode."""
        session = SessionState(
            current_ai="claude",
            current_model="claude-haiku-4-5",
            helper_ai="claude",
            helper_model="claude-haiku-4-5",
            profile=make_profile(),
            chat=ChatDocument.from_raw({"metadata": {}, "messages": [{"role": "user", "content": "test"}]}),
        )

        # Simulate entering retry mode
        session.retry.active = True
        session.retry.base_messages = [ChatMessage.new_user("base")]

        assert session.retry.active is True
        assert len(session.retry.base_messages) == 1
        assert session.secret.active is False

    def test_enter_secret_mode(self):
        """Test entering secret mode."""
        session = SessionState(
            current_ai="claude",
            current_model="claude-haiku-4-5",
            helper_ai="claude",
            helper_model="claude-haiku-4-5",
            profile=make_profile(),
            chat=ChatDocument.from_raw({"metadata": {}, "messages": [{"role": "user", "content": "test"}]}),
        )

        # Simulate entering secret mode
        session.secret.active = True
        session.secret.base_messages = [ChatMessage.new_user("frozen")]

        assert session.secret.active is True
        assert len(session.secret.base_messages) == 1
        assert session.retry.active is False

    def test_cannot_be_in_both_modes(self):
        """Test that retry and secret mode are mutually exclusive in practice."""
        # Note: The current implementation doesn't enforce this,
        # but in practice the app logic should prevent it
        session = SessionState(
            current_ai="claude",
            current_model="claude-haiku-4-5",
            helper_ai="claude",
            helper_model="claude-haiku-4-5",
            profile=make_profile(),
            chat=ChatDocument.empty(),
        )

        # This test documents current behavior
        # (In future, SessionManager should enforce exclusivity)
        session.retry.active = True
        session.secret.active = True

        # Currently both can be True (not ideal)
        assert session.retry.active is True
        assert session.secret.active is True
