"""Unified session management for PolyChat.

This module provides a SessionManager class that wraps SessionState and provides
a clean interface for session management.
"""

from typing import Any, Optional

from .app_state import SessionState, initialize_message_hex_ids, assign_new_message_hex_id
from . import hex_id


class SessionManager:
    """Manages session state with a unified interface.

    This class wraps SessionState and provides:
    - Single source of truth for session data
    - Clean API for state access and modification
    - Encapsulated state transitions (chat switching, mode changes)
    - Automatic hex ID management
    - Provider caching
    - Dict-like access helpers for diagnostics and tests

    Example:
        manager = SessionManager(
            profile=profile_data,
            current_ai="claude",
            current_model="claude-haiku-4-5",
        )

        # Property access (preferred)
        print(manager.current_ai)
        manager.switch_chat(chat_path, chat_data)

        # Dict-like access
        print(manager["current_ai"])
        manager["input_mode"] = "compose"
    """

    def __init__(
        self,
        profile: dict[str, Any],
        current_ai: str,
        current_model: str,
        helper_ai: Optional[str] = None,
        helper_model: Optional[str] = None,
        chat: Optional[dict[str, Any]] = None,
        chat_path: Optional[str] = None,
        profile_path: Optional[str] = None,
        log_file: Optional[str] = None,
        system_prompt: Optional[str] = None,
        system_prompt_path: Optional[str] = None,
        input_mode: str = "quick",
    ):
        """Initialize session manager.

        Args:
            profile: Profile dictionary with configuration
            current_ai: Current AI provider name
            current_model: Current model name
            helper_ai: Helper AI provider name (defaults to current_ai)
            helper_model: Helper model name (defaults to current_model)
            chat: Current chat data (optional)
            chat_path: Current chat file path (optional)
            profile_path: Active profile file path (optional)
            log_file: Active log file path (optional)
            system_prompt: System prompt text (optional)
            system_prompt_path: System prompt path (optional)
            input_mode: Input mode ("quick" or "compose")
        """
        # Use helper AI/model defaults if not specified
        helper_ai = helper_ai or current_ai
        helper_model = helper_model or current_model

        self._state = SessionState(
            current_ai=current_ai,
            current_model=current_model,
            helper_ai=helper_ai,
            helper_model=helper_model,
            profile=profile,
            chat=chat or {},
            chat_path=chat_path,
            profile_path=profile_path,
            log_file=log_file,
            system_prompt=system_prompt,
            system_prompt_path=system_prompt_path,
            input_mode=input_mode,
        )

        # Initialize hex IDs if chat is loaded
        if chat and "messages" in chat:
            initialize_message_hex_ids(self._state)

    # ===================================================================
    # Property Access (Preferred Interface)
    # ===================================================================

    @property
    def current_ai(self) -> str:
        """Current AI provider name."""
        return self._state.current_ai

    @current_ai.setter
    def current_ai(self, value: str) -> None:
        self._state.current_ai = value

    @property
    def current_model(self) -> str:
        """Current model name."""
        return self._state.current_model

    @current_model.setter
    def current_model(self, value: str) -> None:
        self._state.current_model = value

    @property
    def helper_ai(self) -> str:
        """Helper AI provider name."""
        return self._state.helper_ai

    @helper_ai.setter
    def helper_ai(self, value: str) -> None:
        self._state.helper_ai = value

    @property
    def helper_model(self) -> str:
        """Helper model name."""
        return self._state.helper_model

    @helper_model.setter
    def helper_model(self, value: str) -> None:
        self._state.helper_model = value

    @property
    def profile(self) -> dict[str, Any]:
        """Profile dictionary."""
        return self._state.profile

    @property
    def chat(self) -> dict[str, Any]:
        """Current chat data."""
        return self._state.chat

    @property
    def system_prompt(self) -> Optional[str]:
        """System prompt text."""
        return self._state.system_prompt

    @system_prompt.setter
    def system_prompt(self, value: Optional[str]) -> None:
        self._state.system_prompt = value

    @property
    def system_prompt_path(self) -> Optional[str]:
        """System prompt path."""
        return self._state.system_prompt_path

    @system_prompt_path.setter
    def system_prompt_path(self, value: Optional[str]) -> None:
        self._state.system_prompt_path = value

    @property
    def chat_path(self) -> Optional[str]:
        """Current chat file path."""
        return self._state.chat_path

    @chat_path.setter
    def chat_path(self, value: Optional[str]) -> None:
        self._state.chat_path = value

    @property
    def profile_path(self) -> Optional[str]:
        """Current profile file path."""
        return self._state.profile_path

    @profile_path.setter
    def profile_path(self, value: Optional[str]) -> None:
        self._state.profile_path = value

    @property
    def log_file(self) -> Optional[str]:
        """Current log file path."""
        return self._state.log_file

    @log_file.setter
    def log_file(self, value: Optional[str]) -> None:
        self._state.log_file = value

    @property
    def input_mode(self) -> str:
        """Input mode ("quick" or "compose")."""
        return self._state.input_mode

    @input_mode.setter
    def input_mode(self, value: str) -> None:
        if value not in ("quick", "compose"):
            raise ValueError(f"Invalid input mode: {value}. Must be 'quick' or 'compose'")
        self._state.input_mode = value

    @property
    def retry_mode(self) -> bool:
        """Whether retry mode is active."""
        return self._state.retry_mode

    @property
    def secret_mode(self) -> bool:
        """Whether secret mode is active."""
        return self._state.secret_mode

    @property
    def message_hex_ids(self) -> dict[int, str]:
        """Message hex IDs (index → hex_id)."""
        return self._state.message_hex_ids

    @property
    def hex_id_set(self) -> set[str]:
        """Set of all assigned hex IDs."""
        return self._state.hex_id_set

    # ===================================================================
    # Dict-Like Access (Backward Compatibility)
    # ===================================================================

    def __getitem__(self, key: str) -> Any:
        """Get state value by key (dict-like access)."""
        if hasattr(self._state, key):
            return getattr(self._state, key)
        raise KeyError(f"Unknown session key: {key}")

    def __setitem__(self, key: str, value: Any) -> None:
        """Set state value by key (dict-like access)."""
        if hasattr(self._state, key):
            setattr(self._state, key, value)
        else:
            raise KeyError(f"Unknown session key: {key}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get state value with default (dict-like access)."""
        try:
            return self[key]
        except KeyError:
            return default

    def to_dict(self) -> dict[str, Any]:
        """Convert state to a plain dictionary.

        Useful for diagnostics, snapshots, and tests.
        """
        return {
            "current_ai": self._state.current_ai,
            "current_model": self._state.current_model,
            "helper_ai": self._state.helper_ai,
            "helper_model": self._state.helper_model,
            "profile": self._state.profile,
            "chat": self._state.chat,
            "chat_path": self._state.chat_path,
            "profile_path": self._state.profile_path,
            "log_file": self._state.log_file,
            "system_prompt": self._state.system_prompt,
            "system_prompt_path": self._state.system_prompt_path,
            "input_mode": self._state.input_mode,
            "retry_mode": self._state.retry_mode,
            "secret_mode": self._state.secret_mode,
            "message_hex_ids": self._state.message_hex_ids,
            "hex_id_set": self._state.hex_id_set,
        }

    # ===================================================================
    # Chat Management
    # ===================================================================

    def switch_chat(self, chat_path: str, chat_data: dict[str, Any]) -> None:
        """Switch to a different chat.

        This handles all the necessary state transitions:
        - Updates chat data
        - Reinitializes hex IDs
        - Clears retry/secret modes

        Args:
            chat_path: Path to the new chat file
            chat_data: Chat data dictionary
        """
        # Update chat data
        self._state.chat = chat_data
        self._state.chat_path = chat_path

        # Reinitialize hex IDs for new chat
        initialize_message_hex_ids(self._state)

        # Clear chat-scoped state (retry/secret modes)
        self._clear_chat_scoped_state()

    def close_chat(self) -> None:
        """Close current chat and clear related state."""
        self._state.chat = {}
        self._state.chat_path = None
        self._state.message_hex_ids.clear()
        self._state.hex_id_set.clear()
        self._clear_chat_scoped_state()

    def _clear_chat_scoped_state(self) -> None:
        """Clear state that shouldn't leak across chat boundaries."""
        # Clear retry mode
        self._state.retry_mode = False
        self._state.retry_base_messages.clear()
        self._state.retry_current_user_msg = None
        self._state.retry_current_assistant_msg = None

        # Clear secret mode
        self._state.secret_mode = False
        self._state.secret_base_messages.clear()

    # ===================================================================
    # Retry Mode Management
    # ===================================================================

    def enter_retry_mode(self, base_messages: list[dict]) -> None:
        """Enter retry mode with frozen message context.

        Args:
            base_messages: Frozen message context (all messages except last assistant)
        """
        if self._state.secret_mode:
            raise ValueError("Cannot enter retry mode while in secret mode")

        self._state.retry_mode = True
        self._state.retry_base_messages = base_messages.copy()

    def set_retry_attempt(self, user_msg: str, assistant_msg: str) -> None:
        """Store current retry attempt.

        Args:
            user_msg: User message for retry attempt
            assistant_msg: Assistant response for retry attempt
        """
        if not self._state.retry_mode:
            raise ValueError("Not in retry mode")

        self._state.retry_current_user_msg = user_msg
        self._state.retry_current_assistant_msg = assistant_msg

    def get_retry_context(self) -> list[dict]:
        """Get frozen retry context.

        Returns:
            Frozen message context for retry

        Raises:
            ValueError: If not in retry mode
        """
        if not self._state.retry_mode:
            raise ValueError("Not in retry mode")

        return self._state.retry_base_messages

    def get_retry_attempt(self) -> tuple[Optional[str], Optional[str]]:
        """Get current retry attempt messages.

        Returns:
            Tuple of (user_msg, assistant_msg)
        """
        return (
            self._state.retry_current_user_msg,
            self._state.retry_current_assistant_msg,
        )

    def exit_retry_mode(self) -> None:
        """Exit retry mode and clear retry state."""
        self._state.retry_mode = False
        self._state.retry_base_messages.clear()
        self._state.retry_current_user_msg = None
        self._state.retry_current_assistant_msg = None

    # ===================================================================
    # Secret Mode Management
    # ===================================================================

    def enter_secret_mode(self, base_messages: list[dict]) -> None:
        """Enter secret mode with frozen message context.

        Args:
            base_messages: Frozen message context (all current messages)
        """
        if self._state.retry_mode:
            raise ValueError("Cannot enter secret mode while in retry mode")

        self._state.secret_mode = True
        self._state.secret_base_messages = base_messages.copy()

    def get_secret_context(self) -> list[dict]:
        """Get frozen secret context.

        Returns:
            Frozen message context for secret mode

        Raises:
            ValueError: If not in secret mode
        """
        if not self._state.secret_mode:
            raise ValueError("Not in secret mode")

        return self._state.secret_base_messages

    def exit_secret_mode(self) -> None:
        """Exit secret mode and clear secret state."""
        self._state.secret_mode = False
        self._state.secret_base_messages.clear()

    # ===================================================================
    # Hex ID Management
    # ===================================================================

    def assign_message_hex_id(self, message_index: int) -> str:
        """Assign hex ID to a newly added message.

        Args:
            message_index: Index of the message in chat["messages"]

        Returns:
            The generated hex ID
        """
        return assign_new_message_hex_id(self._state, message_index)

    def get_message_hex_id(self, message_index: int) -> Optional[str]:
        """Get hex ID for a message.

        Args:
            message_index: Index of the message

        Returns:
            Hex ID or None if not assigned
        """
        return self._state.message_hex_ids.get(message_index)

    def remove_message_hex_id(self, message_index: int) -> None:
        """Remove hex ID for a message.

        Args:
            message_index: Index of the message
        """
        if message_index in self._state.message_hex_ids:
            hex_to_remove = self._state.message_hex_ids.pop(message_index)
            self._state.hex_id_set.discard(hex_to_remove)

    # ===================================================================
    # Provider Caching
    # ===================================================================

    def get_cached_provider(self, provider_name: str, api_key: str) -> Optional[Any]:
        """Get cached provider instance.

        Args:
            provider_name: Name of the provider
            api_key: API key for the provider

        Returns:
            Cached provider instance or None
        """
        return self._state.get_cached_provider(provider_name, api_key)

    def cache_provider(self, provider_name: str, api_key: str, instance: Any) -> None:
        """Cache a provider instance.

        Args:
            provider_name: Name of the provider
            api_key: API key for the provider
            instance: Provider instance to cache
        """
        self._state.cache_provider(provider_name, api_key, instance)

    # ===================================================================
    # Provider Switching
    # ===================================================================

    def switch_provider(self, provider_name: str, model_name: str) -> None:
        """Switch to a different AI provider and model.

        Args:
            provider_name: Name of the provider
            model_name: Name of the model
        """
        self._state.current_ai = provider_name
        self._state.current_model = model_name

    def toggle_input_mode(self) -> str:
        """Toggle input mode between quick and compose.

        Returns:
            New input mode
        """
        if self._state.input_mode == "quick":
            self._state.input_mode = "compose"
        else:
            self._state.input_mode = "quick"
        return self._state.input_mode
