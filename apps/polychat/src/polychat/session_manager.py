"""Unified session management for PolyChat.

This module provides a SessionManager class that wraps SessionState and provides
a clean interface for session management.
"""

from __future__ import annotations

from typing import Any, Optional

from .ai.types import Citation
from .domain.chat import ChatDocument, ChatMessage, RetryAttempt
from .domain.profile import RuntimeProfile
from .session.state import (
    SessionState,
    assign_new_message_hex_id,
    initialize_message_hex_ids,
)
from .session import operations as session_ops
from . import hex_id
from .session.accessors import (
    StateField,
    state_to_dict,
)
from .prompts.system_prompt import load_system_prompt as resolve_system_prompt
from .timeouts import format_timeout, normalize_timeout


def _validate_input_mode(value: str) -> None:
    """Validate user input mode names accepted by REPL keybindings."""
    if value not in ("quick", "compose"):
        raise ValueError(f"Invalid input mode: {value}. Must be 'quick' or 'compose'")


class SessionManager:
    """Manages session state with a unified interface.

    Wraps SessionState providing single source of truth, clean API for
    state access and modification, encapsulated state transitions,
    automatic hex ID management, and provider caching.
    """

    current_ai = StateField[str]("current_ai")
    current_model = StateField[str]("current_model")
    helper_ai = StateField[str]("helper_ai")
    helper_model = StateField[str]("helper_model")
    profile = StateField[RuntimeProfile]("profile", readonly=True)
    chat = StateField[ChatDocument]("chat", readonly=True)
    system_prompt = StateField[Optional[str]]("system_prompt")
    system_prompt_path = StateField[Optional[str]]("system_prompt_path")
    chat_path = StateField[Optional[str]]("chat_path")
    profile_path = StateField[Optional[str]]("profile_path")
    log_file = StateField[Optional[str]]("log_file")
    input_mode = StateField[str]("input_mode", validator=_validate_input_mode)
    retry_mode = StateField[bool]("retry_mode", coerce=bool)
    secret_mode = StateField[bool]("secret_mode", coerce=bool)
    search_mode = StateField[bool]("search_mode", coerce=bool)
    hex_id_set = StateField[set[str]]("hex_id_set", readonly=True)

    def __init__(
        self,
        profile: RuntimeProfile,
        current_ai: str,
        current_model: str,
        helper_ai: Optional[str] = None,
        helper_model: Optional[str] = None,
        chat: Optional[ChatDocument] = None,
        chat_path: Optional[str] = None,
        profile_path: Optional[str] = None,
        log_file: Optional[str] = None,
        system_prompt: Optional[str] = None,
        system_prompt_path: Optional[str] = None,
        input_mode: str = "quick",
    ):
        """Initialize session manager.

        Args:
            profile: Runtime profile configuration
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

        default_timeout = self._normalize_timeout(profile.timeout)
        profile.timeout = default_timeout
        self._default_timeout = default_timeout

        chat_doc = chat if chat is not None else ChatDocument.empty()

        self._state = SessionState(
            current_ai=current_ai,
            current_model=current_model,
            helper_ai=helper_ai,
            helper_model=helper_model,
            profile=profile,
            chat=chat_doc,
            chat_path=chat_path,
            profile_path=profile_path,
            log_file=log_file,
            system_prompt=system_prompt,
            system_prompt_path=system_prompt_path,
            input_mode=input_mode,
        )

        # Initialize hex IDs if chat has messages
        if chat_doc.messages:
            initialize_message_hex_ids(self._state)

    @property
    def message_hex_ids(self) -> dict[int, str]:
        """Message hex IDs (index → hex_id)."""
        return hex_id.build_hex_map(self._state.chat.messages)

    # ===================================================================
    # Serialization
    # ===================================================================

    def to_dict(self) -> dict[str, Any]:
        """Convert state to a plain dictionary for diagnostics and tests."""
        return state_to_dict(self._state, message_hex_ids=self.message_hex_ids)

    # ===================================================================
    # Chat Management
    # ===================================================================

    def switch_chat(self, chat_path: str, chat_data: ChatDocument) -> None:
        """Switch to a different chat.

        This handles all the necessary state transitions:
        - Updates chat data
        - Reinitializes hex IDs
        - Clears retry/secret modes

        Args:
            chat_path: Path to the new chat file
            chat_data: Chat data (ChatDocument)
        """
        session_ops.switch_chat(
            self._state,
            chat_path,
            chat_data,
            system_prompt_path=self._state.system_prompt_path,
        )

    def close_chat(self) -> None:
        """Close current chat and clear related state."""
        session_ops.close_chat(self._state)

    def _clear_chat_scoped_state(self) -> None:
        """Clear state that shouldn't leak across chat boundaries."""
        session_ops.clear_chat_scoped_state(self._state)

    def clear_chat_scoped_state(self) -> None:
        """Public wrapper to clear retry/secret state."""
        self._clear_chat_scoped_state()

    @staticmethod
    def _normalize_timeout(value: Any) -> int | float:
        """Normalize timeout to int/float and reject invalid values."""
        return normalize_timeout(value)

    @staticmethod
    def format_timeout(timeout: int | float) -> str:
        """Format timeout value for user-facing messages."""
        return format_timeout(timeout)

    @property
    def default_timeout(self) -> int | float:
        """Initial timeout loaded from profile at session start."""
        return self._default_timeout

    def set_timeout(self, timeout: Any) -> int | float:
        """Update active timeout and invalidate provider cache."""
        normalized = self._normalize_timeout(timeout)
        self._state.profile.timeout = normalized
        self.clear_provider_cache()
        return normalized

    def reset_timeout_to_default(self) -> int | float:
        """Reset active timeout back to the session's profile default."""
        return self.set_timeout(self._default_timeout)

    def clear_provider_cache(self) -> None:
        """Clear all cached provider instances."""
        session_ops.clear_provider_cache(self._state)

    async def save_current_chat(
        self,
        *,
        chat_path: Optional[str] = None,
        chat_data: Optional[ChatDocument] = None,
    ) -> bool:
        """Persist current chat state.

        Args:
            chat_path: Optional explicit path override.
            chat_data: Optional explicit chat data override.

        Returns:
            True when a save was performed, False when skipped.
        """
        return await session_ops.save_current_chat(
            self._state,
            chat_path=chat_path,
            chat_data=chat_data,
        )

    @staticmethod
    def load_system_prompt(
        profile_data: RuntimeProfile,
        profile_path: Optional[str] = None,
        strict: bool = False,
    ) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """Resolve and load system prompt content from profile data.

        Args:
            profile_data: RuntimeProfile instance
            profile_path: Optional raw profile path for preserving original system_prompt text
            strict: If True, raise ValueError when path-based prompt loading fails

        Returns:
            Tuple of (system_prompt_text, system_prompt_path, warning_message)
        """
        return resolve_system_prompt(
            profile_data,
            profile_path=profile_path,
            strict=strict,
        )

    # ===================================================================
    # Retry Mode Management
    # ===================================================================

    def enter_retry_mode(self, base_messages: list[ChatMessage], target_index: int | None = None) -> None:
        """Enter retry mode with frozen message context.

        Args:
            base_messages: Frozen message context (all messages except last assistant)
            target_index: Index of the message that /apply should replace
        """
        session_ops.enter_retry_mode(
            self._state,
            base_messages,
            target_index=target_index,
        )

    def get_retry_context(self) -> list[ChatMessage]:
        """Get frozen retry context.

        Returns:
            Frozen message context for retry

        Raises:
            ValueError: If not in retry mode
        """
        return session_ops.get_retry_context(self._state)

    def add_retry_attempt(
        self,
        user_msg: str,
        assistant_msg: str,
        retry_hex_id: Optional[str] = None,
        citations: Optional[list[Citation]] = None,
    ) -> str:
        """Store a retry attempt and return its runtime hex ID."""
        return session_ops.add_retry_attempt(
            self._state,
            user_msg,
            assistant_msg,
            retry_hex_id=retry_hex_id,
            citations=citations,
        )

    def get_retry_attempt(self, retry_hex_id: str) -> Optional[RetryAttempt]:
        """Get one retry attempt by runtime hex ID."""
        return session_ops.get_retry_attempt(self._state, retry_hex_id)

    def get_latest_retry_attempt_id(self) -> Optional[str]:
        """Get the most recently generated retry attempt hex ID."""
        return session_ops.get_latest_retry_attempt_id(self._state)

    def get_retry_target_index(self) -> Optional[int]:
        """Get the chat message index that /apply should replace."""
        return session_ops.get_retry_target_index(self._state)

    def reserve_hex_id(self) -> str:
        """Reserve a runtime hex ID for an in-flight assistant response."""
        return session_ops.reserve_hex_id(self._state)

    def release_hex_id(self, message_hex_id: str) -> None:
        """Release a runtime hex ID that was reserved but not persisted."""
        session_ops.release_hex_id(self._state, message_hex_id)

    def exit_retry_mode(self) -> None:
        """Exit retry mode and clear retry state."""
        session_ops.exit_retry_mode(self._state)

    # ===================================================================
    # Secret Mode Management
    # ===================================================================

    def enter_secret_mode(self, base_messages: list[ChatMessage]) -> None:
        """Enter secret mode and store a snapshot of persisted context.

        Args:
            base_messages: Current persisted message context
        """
        session_ops.enter_secret_mode(self._state, base_messages)

    def get_secret_context(self) -> list[ChatMessage]:
        """Get stored secret-mode context snapshot.

        Returns:
            Snapshot captured when secret mode was enabled

        Raises:
            ValueError: If not in secret mode
        """
        return session_ops.get_secret_context(self._state)

    def exit_secret_mode(self) -> None:
        """Exit secret mode and clear secret state."""
        session_ops.exit_secret_mode(self._state)

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
        return session_ops.get_message_hex_id(self._state, message_index)

    def remove_message_hex_id(self, message_index: int) -> None:
        """Remove hex ID for a message.

        Args:
            message_index: Index of the message
        """
        session_ops.remove_message_hex_id(self._state, message_index)

    def pop_message(
        self,
        message_index: int = -1,
        chat_data: Optional[ChatDocument] = None,
    ) -> Optional[Any]:
        """Pop a message and atomically clean up its runtime hex ID.

        Args:
            message_index: Index to pop (default: -1 for last message)
            chat_data: Optional chat object override (defaults to current session chat)

        Returns:
            Popped ChatMessage, or None when the chat has no messages.
        """
        return session_ops.pop_message(
            self._state,
            message_index=message_index,
            chat_data=chat_data,
        )

    # ===================================================================
    # Provider Caching
    # ===================================================================

    def get_cached_provider(
        self,
        provider_name: str,
        api_key: str,
        timeout_sec: int | float | None = None,
    ) -> Optional[Any]:
        """Get cached provider instance.

        Args:
            provider_name: Name of the provider
            api_key: API key for the provider
            timeout_sec: Effective timeout used to build provider instance

        Returns:
            Cached provider instance or None
        """
        return session_ops.get_cached_provider(
            self._state,
            provider_name,
            api_key,
            timeout_sec=timeout_sec,
        )

    def cache_provider(
        self,
        provider_name: str,
        api_key: str,
        instance: Any,
        timeout_sec: int | float | None = None,
    ) -> None:
        """Cache a provider instance.

        Args:
            provider_name: Name of the provider
            api_key: API key for the provider
            instance: Provider instance to cache
            timeout_sec: Effective timeout used to build provider instance
        """
        session_ops.cache_provider(
            self._state,
            provider_name,
            api_key,
            instance,
            timeout_sec=timeout_sec,
        )

    # ===================================================================
    # Provider Switching
    # ===================================================================

    def switch_provider(self, provider_name: str, model_name: str) -> None:
        """Switch to a different AI provider and model.

        Args:
            provider_name: Name of the provider
            model_name: Name of the model
        """
        session_ops.switch_provider(self._state, provider_name, model_name)

    def toggle_input_mode(self) -> str:
        """Toggle input mode between quick and compose.

        Returns:
            New input mode
        """
        return session_ops.toggle_input_mode(self._state)
