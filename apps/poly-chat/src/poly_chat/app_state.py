"""Session state container and shared state utilities for PolyChat."""

import math
from dataclasses import dataclass, field
from typing import Any, Optional

from . import hex_id


@dataclass
class SessionState:
    """Session state for the REPL loop."""

    current_ai: str
    current_model: str
    helper_ai: str
    helper_model: str
    profile: dict[str, Any]
    chat: dict[str, Any]
    chat_path: Optional[str] = None
    profile_path: Optional[str] = None
    log_file: Optional[str] = None
    system_prompt: Optional[str] = None
    system_prompt_path: Optional[str] = None
    input_mode: str = "quick"
    retry_mode: bool = False
    retry_base_messages: list = field(default_factory=list)
    retry_target_index: Optional[int] = None
    retry_attempts: dict[str, dict[str, Any]] = field(default_factory=dict)
    secret_mode: bool = False
    secret_base_messages: list = field(default_factory=list)
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
        instance = self._provider_cache.get(key)
        if instance is not None:
            return instance
        # Backward-compat for tests/older cache entries keyed without timeout.
        return self._provider_cache.get((provider_name, api_key))  # type: ignore[arg-type]

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

    if session.chat and "messages" in session.chat:
        for message in session.chat["messages"]:
            message["hex_id"] = hex_id.generate_hex_id(session.hex_id_set)


def assign_new_message_hex_id(session: SessionState, message_index: int) -> str:
    """Assign hex ID to a newly added message."""
    messages = session.chat.get("messages", []) if isinstance(session.chat, dict) else []
    if message_index < 0 or message_index >= len(messages):
        raise IndexError(f"Message index {message_index} out of range")

    new_hex_id = hex_id.generate_hex_id(session.hex_id_set)
    messages[message_index]["hex_id"] = new_hex_id
    return new_hex_id


def has_pending_error(chat_data: dict) -> bool:
    """Check if chat has a pending error that blocks normal conversation."""
    if not chat_data or "messages" not in chat_data:
        return False

    messages = chat_data["messages"]
    if not messages:
        return False

    return messages[-1].get("role") == "error"


def pending_error_guidance(*, compact: bool = False) -> str:
    """Return user guidance when a chat has a pending error."""
    if compact:
        return "[⚠️  PENDING ERROR - Use /retry or /rewind]"

    return (
        "\n⚠️  Cannot continue: last interaction failed.\n"
        "Use /retry to rerun the same message.\n"
        "Use /rewind to remove the failed error/turn."
    )
