"""Tests for SessionManager - unified session state management."""

import json

import pytest
from src.poly_chat.session_manager import SessionManager


class TestSessionManagerCreation:
    """Test SessionManager initialization."""

    def test_create_minimal_manager(self):
        """Test creating manager with minimal required arguments."""
        manager = SessionManager(
            profile={"timeout": 30},
            current_ai="claude",
            current_model="claude-haiku-4-5",
        )

        assert manager.current_ai == "claude"
        assert manager.current_model == "claude-haiku-4-5"
        assert manager.helper_ai == "claude"  # Defaults to current_ai
        assert manager.helper_model == "claude-haiku-4-5"  # Defaults to current_model
        assert manager.profile == {"timeout": 30}
        assert manager.chat == {}
        assert manager.input_mode == "quick"

    def test_create_with_explicit_helper(self):
        """Test creating manager with explicit helper AI."""
        manager = SessionManager(
            profile={},
            current_ai="claude",
            current_model="claude-haiku-4-5",
            helper_ai="openai",
            helper_model="gpt-5-mini",
        )

        assert manager.current_ai == "claude"
        assert manager.helper_ai == "openai"
        assert manager.helper_model == "gpt-5-mini"

    def test_create_with_chat(self):
        """Test creating manager with existing chat."""
        chat_data = {
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi"},
            ]
        }

        manager = SessionManager(
            profile={},
            current_ai="claude",
            current_model="claude-haiku-4-5",
            chat=chat_data,
        )

        assert manager.chat == chat_data
        # Hex IDs should be initialized
        assert len(manager.message_hex_ids) == 2
        assert len(manager.hex_id_set) == 2

    def test_create_tracks_default_timeout_and_strict_prompt_policy(self):
        manager = SessionManager(
            profile={"timeout": 45, "system_prompt_strict": True},
            current_ai="claude",
            current_model="claude-haiku-4-5",
        )

        assert manager.default_timeout == 45
        assert manager.profile["timeout"] == 45
        assert manager.strict_system_prompt is True

    def test_create_allows_strict_prompt_override(self):
        manager = SessionManager(
            profile={"timeout": 45, "system_prompt_strict": False},
            current_ai="claude",
            current_model="claude-haiku-4-5",
            strict_system_prompt=True,
        )

        assert manager.strict_system_prompt is True


class TestSystemPromptLoading:
    """Test SessionManager system prompt loading."""

    def test_load_system_prompt_from_inline_content(self):
        profile_data = {"system_prompt": {"type": "text", "content": "Inline prompt"}}

        prompt, prompt_path, warning = SessionManager.load_system_prompt(profile_data)

        assert prompt == "Inline prompt"
        assert prompt_path is None
        assert warning is None

    def test_load_system_prompt_from_file(self, tmp_path):
        prompt_file = tmp_path / "prompt.txt"
        prompt_file.write_text("Prompt from file\n", encoding="utf-8")
        profile_data = {"system_prompt": str(prompt_file)}

        prompt, prompt_path, warning = SessionManager.load_system_prompt(profile_data)

        assert prompt == "Prompt from file"
        assert prompt_path == str(prompt_file)
        assert warning is None

    def test_load_system_prompt_returns_warning_on_missing_file(self):
        profile_data = {"system_prompt": "/tmp/nonexistent-prompt-file.txt"}

        prompt, prompt_path, warning = SessionManager.load_system_prompt(profile_data)

        assert prompt is None
        assert prompt_path == "/tmp/nonexistent-prompt-file.txt"
        assert warning is not None

    def test_load_system_prompt_strict_raises_on_missing_file(self):
        profile_data = {"system_prompt": "/tmp/nonexistent-prompt-file.txt"}

        with pytest.raises(ValueError, match="Could not load system prompt"):
            SessionManager.load_system_prompt(profile_data, strict=True)

    def test_load_system_prompt_uses_raw_profile_path_when_available(self, tmp_path):
        prompt_file = tmp_path / "prompt.txt"
        prompt_file.write_text("Raw profile path prompt", encoding="utf-8")
        profile_file = tmp_path / "profile.json"
        profile_file.write_text(
            json.dumps({"system_prompt": str(prompt_file)}), encoding="utf-8"
        )
        # Simulate load_profile-mapped value while preserving a raw profile source.
        profile_data = {"system_prompt": str(prompt_file.resolve())}

        prompt, prompt_path, warning = SessionManager.load_system_prompt(
            profile_data,
            str(profile_file),
        )

        assert prompt == "Raw profile path prompt"
        assert prompt_path == str(prompt_file)
        assert warning is None


class TestPropertyAccess:
    """Test property-based access (preferred interface)."""

    def test_read_properties(self):
        """Test reading properties."""
        manager = SessionManager(
            profile={"timeout": 30},
            current_ai="claude",
            current_model="claude-haiku-4-5",
            system_prompt="Be helpful",
            input_mode="compose",
        )

        assert manager.current_ai == "claude"
        assert manager.current_model == "claude-haiku-4-5"
        assert manager.profile == {"timeout": 30}
        assert manager.system_prompt == "Be helpful"
        assert manager.input_mode == "compose"
        assert manager.retry_mode is False
        assert manager.secret_mode is False

    def test_write_properties(self):
        """Test writing properties."""
        manager = SessionManager(
            profile={},
            current_ai="claude",
            current_model="claude-haiku-4-5",
        )

        # Update properties
        manager.current_ai = "openai"
        manager.current_model = "gpt-5-mini"
        manager.system_prompt = "New prompt"
        manager.input_mode = "compose"

        assert manager.current_ai == "openai"
        assert manager.current_model == "gpt-5-mini"
        assert manager.system_prompt == "New prompt"
        assert manager.input_mode == "compose"

    def test_invalid_input_mode_rejected(self):
        """Test that invalid input mode is rejected."""
        manager = SessionManager(
            profile={},
            current_ai="claude",
            current_model="claude-haiku-4-5",
        )

        with pytest.raises(ValueError, match="Invalid input mode"):
            manager.input_mode = "invalid"


class TestTimeoutManagement:
    def test_set_timeout_normalizes_and_clears_cache(self):
        manager = SessionManager(
            profile={"timeout": 30},
            current_ai="claude",
            current_model="claude-haiku-4-5",
        )
        manager.cache_provider("claude", "k", object())

        timeout = manager.set_timeout(60.0)

        assert timeout == 60
        assert manager.profile["timeout"] == 60
        assert manager.get_cached_provider("claude", "k") is None

    def test_reset_timeout_to_default_uses_startup_value(self):
        manager = SessionManager(
            profile={"timeout": 30},
            current_ai="claude",
            current_model="claude-haiku-4-5",
        )
        manager.profile["timeout"] = 90

        timeout = manager.reset_timeout_to_default()

        assert timeout == 30
        assert manager.profile["timeout"] == 30


class TestDictLikeAccess:
    """Test dict-like access (backward compatibility)."""

    def test_getitem_access(self):
        """Test accessing values via dict-like syntax."""
        manager = SessionManager(
            profile={"timeout": 30},
            current_ai="claude",
            current_model="claude-haiku-4-5",
        )

        assert manager["current_ai"] == "claude"
        assert manager["current_model"] == "claude-haiku-4-5"
        assert manager["profile"] == {"timeout": 30}
        assert manager["input_mode"] == "quick"

    def test_setitem_access(self):
        """Test setting values via dict-like syntax."""
        manager = SessionManager(
            profile={},
            current_ai="claude",
            current_model="claude-haiku-4-5",
        )

        manager["current_ai"] = "openai"
        manager["input_mode"] = "compose"

        assert manager["current_ai"] == "openai"
        assert manager["input_mode"] == "compose"

    def test_get_with_default(self):
        """Test get() method with default value."""
        manager = SessionManager(
            profile={},
            current_ai="claude",
            current_model="claude-haiku-4-5",
        )

        assert manager.get("current_ai") == "claude"
        assert manager.get("nonexistent", "default") == "default"

    def test_invalid_key_raises_error(self):
        """Test that accessing invalid key raises KeyError."""
        manager = SessionManager(
            profile={},
            current_ai="claude",
            current_model="claude-haiku-4-5",
        )

        with pytest.raises(KeyError, match="Unknown session key"):
            _ = manager["invalid_key"]

    def test_to_dict_conversion(self):
        """Test converting manager to dictionary."""
        manager = SessionManager(
            profile={"timeout": 30},
            current_ai="claude",
            current_model="claude-haiku-4-5",
            input_mode="compose",
        )

        session_dict = manager.to_dict()

        assert isinstance(session_dict, dict)
        assert session_dict["current_ai"] == "claude"
        assert session_dict["current_model"] == "claude-haiku-4-5"
        assert session_dict["profile"] == {"timeout": 30}
        assert session_dict["input_mode"] == "compose"
        assert session_dict["retry_mode"] is False


class TestChatManagement:
    """Test chat switching and lifecycle management."""

    def test_switch_chat(self):
        """Test switching to a different chat."""
        manager = SessionManager(
            profile={},
            current_ai="claude",
            current_model="claude-haiku-4-5",
            chat={"messages": [{"role": "user", "content": "old"}]},
        )

        # Enter retry mode to test that it gets cleared
        manager.enter_retry_mode([{"role": "user", "content": "old"}])
        assert manager.retry_mode is True

        # Switch to new chat
        new_chat = {"messages": [{"role": "user", "content": "new"}]}
        manager.switch_chat("/path/to/new.json", new_chat)

        # Chat should be updated
        assert manager.chat == new_chat

        # Hex IDs should be reinitialized
        assert len(manager.message_hex_ids) == 1

        # Retry mode should be cleared
        assert manager.retry_mode is False

    def test_switch_chat_backfills_missing_system_prompt_metadata(self):
        """Switching to old chats should backfill missing system prompt metadata."""
        manager = SessionManager(
            profile={},
            current_ai="claude",
            current_model="claude-haiku-4-5",
            system_prompt_path="@/system-prompts/default.txt",
        )

        new_chat = {
            "metadata": {"title": "Legacy", "system_prompt_path": None},
            "messages": [],
        }
        manager.switch_chat("/path/to/new.json", new_chat)
        assert manager.chat["metadata"]["system_prompt_path"] == "@/system-prompts/default.txt"

    def test_close_chat(self):
        """Test closing current chat."""
        manager = SessionManager(
            profile={},
            current_ai="claude",
            current_model="claude-haiku-4-5",
            chat={"messages": [{"role": "user", "content": "test"}]},
        )

        # Set up some state
        manager.enter_secret_mode([{"role": "user", "content": "test"}])

        # Close chat
        manager.close_chat()

        # Chat should be empty
        assert manager.chat == {}

        # Hex IDs should be cleared
        assert manager.message_hex_ids == {}
        assert manager.hex_id_set == set()

        # Secret mode should be cleared
        assert manager.secret_mode is False


class TestRetryModeManagement:
    """Test retry mode operations."""

    def test_enter_retry_mode(self):
        """Test entering retry mode."""
        manager = SessionManager(
            profile={},
            current_ai="claude",
            current_model="claude-haiku-4-5",
        )

        base_messages = [{"role": "user", "content": "question"}]
        manager.enter_retry_mode(base_messages)

        assert manager.retry_mode is True
        assert manager.get_retry_context() == base_messages

    def test_cannot_enter_retry_while_in_secret_mode(self):
        """Test that entering retry mode while in secret mode raises error."""
        manager = SessionManager(
            profile={},
            current_ai="claude",
            current_model="claude-haiku-4-5",
        )

        manager.enter_secret_mode([])

        with pytest.raises(ValueError, match="Cannot enter retry mode while in secret mode"):
            manager.enter_retry_mode([])

    def test_set_and_get_retry_attempt(self):
        """Test storing and retrieving retry attempt."""
        manager = SessionManager(
            profile={},
            current_ai="claude",
            current_model="claude-haiku-4-5",
        )

        manager.enter_retry_mode([{"role": "user", "content": "base"}])
        manager.set_retry_attempt("new question", "new answer")

        user_msg, assistant_msg = manager.get_retry_attempt()
        assert user_msg == "new question"
        assert assistant_msg == "new answer"

    def test_set_retry_attempt_without_mode_raises_error(self):
        """Test that setting retry attempt outside retry mode raises error."""
        manager = SessionManager(
            profile={},
            current_ai="claude",
            current_model="claude-haiku-4-5",
        )

        with pytest.raises(ValueError, match="Not in retry mode"):
            manager.set_retry_attempt("test", "test")

    def test_get_retry_context_without_mode_raises_error(self):
        """Test that getting retry context outside retry mode raises error."""
        manager = SessionManager(
            profile={},
            current_ai="claude",
            current_model="claude-haiku-4-5",
        )

        with pytest.raises(ValueError, match="Not in retry mode"):
            manager.get_retry_context()

    def test_exit_retry_mode(self):
        """Test exiting retry mode clears all state."""
        manager = SessionManager(
            profile={},
            current_ai="claude",
            current_model="claude-haiku-4-5",
        )

        manager.enter_retry_mode([{"role": "user", "content": "base"}])
        manager.set_retry_attempt("question", "answer")

        manager.exit_retry_mode()

        assert manager.retry_mode is False
        user_msg, assistant_msg = manager.get_retry_attempt()
        assert user_msg is None
        assert assistant_msg is None


class TestSecretModeManagement:
    """Test secret mode operations."""

    def test_enter_secret_mode(self):
        """Test entering secret mode."""
        manager = SessionManager(
            profile={},
            current_ai="claude",
            current_model="claude-haiku-4-5",
        )

        base_messages = [
            {"role": "user", "content": "public"},
            {"role": "assistant", "content": "response"},
        ]
        manager.enter_secret_mode(base_messages)

        assert manager.secret_mode is True
        assert manager.get_secret_context() == base_messages

    def test_cannot_enter_secret_while_in_retry_mode(self):
        """Test that entering secret mode while in retry mode raises error."""
        manager = SessionManager(
            profile={},
            current_ai="claude",
            current_model="claude-haiku-4-5",
        )

        manager.enter_retry_mode([])

        with pytest.raises(ValueError, match="Cannot enter secret mode while in retry mode"):
            manager.enter_secret_mode([])

    def test_get_secret_context_without_mode_raises_error(self):
        """Test that getting secret context outside secret mode raises error."""
        manager = SessionManager(
            profile={},
            current_ai="claude",
            current_model="claude-haiku-4-5",
        )

        with pytest.raises(ValueError, match="Not in secret mode"):
            manager.get_secret_context()

    def test_exit_secret_mode(self):
        """Test exiting secret mode clears all state."""
        manager = SessionManager(
            profile={},
            current_ai="claude",
            current_model="claude-haiku-4-5",
        )

        manager.enter_secret_mode([{"role": "user", "content": "frozen"}])
        manager.exit_secret_mode()

        assert manager.secret_mode is False


class TestHexIdManagement:
    """Test hex ID assignment and management."""

    def test_assign_message_hex_id(self):
        """Test assigning hex ID to a new message."""
        manager = SessionManager(
            profile={},
            current_ai="claude",
            current_model="claude-haiku-4-5",
            chat={"messages": [{"role": "user", "content": "Hello"}]},
        )

        # Should have 1 hex ID from initialization
        assert len(manager.message_hex_ids) == 1

        # Add a second message, then assign ID
        manager.chat["messages"].append({"role": "assistant", "content": "Hi"})

        # Assign new hex ID for second message
        hex_id = manager.assign_message_hex_id(1)

        assert hex_id in manager.hex_id_set
        assert manager.message_hex_ids[1] == hex_id
        assert len(manager.message_hex_ids) == 2

    def test_get_message_hex_id(self):
        """Test getting hex ID for a message."""
        manager = SessionManager(
            profile={},
            current_ai="claude",
            current_model="claude-haiku-4-5",
            chat={"messages": [{"role": "user", "content": "Hello"}]},
        )

        hex_id = manager.get_message_hex_id(0)
        assert hex_id is not None
        assert hex_id in manager.hex_id_set

        # Nonexistent index returns None
        assert manager.get_message_hex_id(999) is None

    def test_remove_message_hex_id(self):
        """Test removing hex ID for a message."""
        manager = SessionManager(
            profile={},
            current_ai="claude",
            current_model="claude-haiku-4-5",
            chat={"messages": [{"role": "user", "content": "Hello"}]},
        )

        initial_count = len(manager.message_hex_ids)
        hex_id = manager.get_message_hex_id(0)

        # Remove hex ID
        manager.remove_message_hex_id(0)

        assert len(manager.message_hex_ids) == initial_count - 1
        assert hex_id not in manager.hex_id_set
        assert manager.get_message_hex_id(0) is None

    def test_pop_message_removes_hex_id_from_set(self):
        """Popping a message should atomically clean up its hex_id tracking."""
        manager = SessionManager(
            profile={},
            current_ai="claude",
            current_model="claude-haiku-4-5",
            chat={
                "messages": [
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi"},
                ]
            },
        )
        popped_hex = manager.get_message_hex_id(1)
        assert popped_hex in manager.hex_id_set

        popped = manager.pop_message()

        assert popped is not None
        assert popped_hex not in manager.hex_id_set
        assert len(manager.chat["messages"]) == 1

    def test_pop_message_with_explicit_chat_data(self):
        """pop_message should support explicit chat objects used by orchestrator."""
        manager = SessionManager(
            profile={},
            current_ai="claude",
            current_model="claude-haiku-4-5",
        )
        chat_data = {
            "messages": [
                {"role": "user", "content": "Hello", "hex_id": "abc"},
            ]
        }
        manager._state.hex_id_set.add("abc")

        popped = manager.pop_message(-1, chat_data)

        assert popped is not None
        assert manager.hex_id_set == set()


class TestProviderCaching:
    """Test provider instance caching."""

    def test_cache_and_retrieve_provider(self):
        """Test caching and retrieving provider."""
        manager = SessionManager(
            profile={},
            current_ai="claude",
            current_model="claude-haiku-4-5",
        )

        mock_provider = {"name": "claude", "api_key": "test"}

        manager.cache_provider("claude", "sk-test-key", mock_provider)
        cached = manager.get_cached_provider("claude", "sk-test-key")

        assert cached == mock_provider

    def test_cache_miss_returns_none(self):
        """Test that cache miss returns None."""
        manager = SessionManager(
            profile={},
            current_ai="claude",
            current_model="claude-haiku-4-5",
        )

        cached = manager.get_cached_provider("nonexistent", "key")
        assert cached is None


class TestProviderSwitching:
    """Test provider switching operations."""

    def test_switch_provider(self):
        """Test switching to different provider."""
        manager = SessionManager(
            profile={},
            current_ai="claude",
            current_model="claude-haiku-4-5",
        )

        manager.switch_provider("openai", "gpt-5-mini")

        assert manager.current_ai == "openai"
        assert manager.current_model == "gpt-5-mini"

    def test_toggle_input_mode(self):
        """Test toggling input mode."""
        manager = SessionManager(
            profile={},
            current_ai="claude",
            current_model="claude-haiku-4-5",
            input_mode="quick",
        )

        # Toggle to compose
        new_mode = manager.toggle_input_mode()
        assert new_mode == "compose"
        assert manager.input_mode == "compose"

        # Toggle back to quick
        new_mode = manager.toggle_input_mode()
        assert new_mode == "quick"
        assert manager.input_mode == "quick"


class TestStateSafety:
    """Test that SessionManager enforces state safety."""

    def test_modes_are_mutually_exclusive(self):
        """Test that retry and secret modes are mutually exclusive."""
        manager = SessionManager(
            profile={},
            current_ai="claude",
            current_model="claude-haiku-4-5",
        )

        # Enter retry mode
        manager.enter_retry_mode([])
        assert manager.retry_mode is True

        # Cannot enter secret mode
        with pytest.raises(ValueError):
            manager.enter_secret_mode([])

        # Exit retry, enter secret
        manager.exit_retry_mode()
        manager.enter_secret_mode([])
        assert manager.secret_mode is True

        # Cannot enter retry mode
        with pytest.raises(ValueError):
            manager.enter_retry_mode([])
