"""Session state container and shared state utilities for PolyChat."""

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
    retry_current_user_msg: Optional[str] = None
    retry_current_assistant_msg: Optional[str] = None
    secret_mode: bool = False
    secret_base_messages: list = field(default_factory=list)
    message_hex_ids: dict[int, str] = field(default_factory=dict)
    hex_id_set: set[str] = field(default_factory=set)
    _provider_cache: dict[tuple[str, str], Any] = field(default_factory=dict)

    def get_cached_provider(self, provider_name: str, api_key: str) -> Optional[Any]:
        """Get cached provider instance if available."""
        return self._provider_cache.get((provider_name, api_key))

    def cache_provider(self, provider_name: str, api_key: str, instance: Any) -> None:
        """Cache a provider instance."""
        self._provider_cache[(provider_name, api_key)] = instance


def initialize_message_hex_ids(session: SessionState) -> None:
    """Initialize hex IDs for all messages in the current chat."""
    session.message_hex_ids.clear()
    session.hex_id_set.clear()

    if session.chat and "messages" in session.chat:
        message_count = len(session.chat["messages"])
        session.message_hex_ids = hex_id.assign_hex_ids(
            message_count, session.hex_id_set
        )


def assign_new_message_hex_id(session: SessionState, message_index: int) -> str:
    """Assign hex ID to a newly added message."""
    new_hex_id = hex_id.generate_hex_id(session.hex_id_set)
    session.message_hex_ids[message_index] = new_hex_id
    return new_hex_id


def has_pending_error(chat_data: dict) -> bool:
    """Check if chat has a pending error that blocks normal conversation."""
    if not chat_data or "messages" not in chat_data:
        return False

    messages = chat_data["messages"]
    if not messages:
        return False

    return messages[-1].get("role") == "error"
