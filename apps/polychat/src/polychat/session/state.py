"""Session state model and state-scoped helpers."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Optional

from .. import hex_id
from ..domain.chat import ChatDocument, ChatMessage, RetryAttempt
from ..domain.profile import RuntimeProfile


EMOJI_WARNING = "⚠️"


@dataclass
class SessionState:
    """Session state for the REPL loop."""

    current_ai: str
    current_model: str
    helper_ai: str
    helper_model: str
    profile: RuntimeProfile
    chat: ChatDocument
    chat_path: Optional[str] = None
    profile_path: Optional[str] = None
    log_file: Optional[str] = None
    system_prompt: Optional[str] = None
    system_prompt_path: Optional[str] = None
    input_mode: str = "quick"
    retry_mode: bool = False
    retry_base_messages: list[ChatMessage] = field(default_factory=list)
    retry_target_index: Optional[int] = None
    retry_attempts: dict[str, RetryAttempt] = field(default_factory=dict)
    secret_mode: bool = False
    secret_base_messages: list[ChatMessage] = field(default_factory=list)
    search_mode: bool = False
    hex_id_set: set[str] = field(default_factory=set)
    _provider_cache: dict[tuple[str, str, int | float | None], Any] = field(
        default_factory=dict
    )

    @staticmethod
    def _normalize_timeout_key(timeout_sec: int | float | None) -> int | float | None:
        if timeout_sec is None:
            return None
        if isinstance(timeout_sec, bool) or not isinstance(timeout_sec, (int, float)):
            return None
        numeric = float(timeout_sec)
        if not math.isfinite(numeric):
            return None
        if numeric.is_integer():
            return int(numeric)
        return numeric

    def _provider_cache_key(
        self,
        provider_name: str,
        api_key: str,
        timeout_sec: int | float | None = None,
    ) -> tuple[str, str, int | float | None]:
        return (
            provider_name,
            api_key,
            self._normalize_timeout_key(timeout_sec),
        )

    def get_cached_provider(
        self,
        provider_name: str,
        api_key: str,
        timeout_sec: int | float | None = None,
    ) -> Optional[Any]:
        """Get cached provider instance if available."""
        key = self._provider_cache_key(provider_name, api_key, timeout_sec=timeout_sec)
        return self._provider_cache.get(key) or None

    def cache_provider(
        self,
        provider_name: str,
        api_key: str,
        instance: Any,
        timeout_sec: int | float | None = None,
    ) -> None:
        """Cache a provider instance."""
        key = self._provider_cache_key(provider_name, api_key, timeout_sec=timeout_sec)
        self._provider_cache[key] = instance

    def clear_provider_cache(self) -> None:
        """Clear all cached provider instances."""
        self._provider_cache.clear()


def initialize_message_hex_ids(session: SessionState) -> None:
    """Initialize hex IDs for all messages in the current chat."""
    session.hex_id_set.clear()

    for message in session.chat.messages:
        message.hex_id = hex_id.generate_hex_id(session.hex_id_set)


def assign_new_message_hex_id(session: SessionState, message_index: int) -> str:
    """Assign hex ID to a newly added message."""
    messages = session.chat.messages
    if message_index < 0 or message_index >= len(messages):
        raise IndexError(f"Message index {message_index} out of range")

    new_hex_id = hex_id.generate_hex_id(session.hex_id_set)
    messages[message_index].hex_id = new_hex_id
    return new_hex_id


def has_pending_error(chat_data: ChatDocument | None) -> bool:
    """Check if chat has a pending error that blocks normal conversation."""
    if chat_data is None:
        return False

    messages = chat_data.messages
    if not messages:
        return False
    last_message = messages[-1]
    return bool(last_message.role == "error")


def pending_error_guidance(*, compact: bool = False) -> str:
    """Return user guidance when a chat has a pending error."""
    if compact:
        return f"[{EMOJI_WARNING} PENDING ERROR - Use /retry or /rewind]"

    return (
        f"{EMOJI_WARNING} Cannot continue: last interaction failed.\n"
        "Use /retry to rerun the same message.\n"
        "Use /rewind to remove the failed error/turn."
    )
