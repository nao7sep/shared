"""Chat lifecycle transitions for session state."""

from __future__ import annotations

from typing import Any

from . import modes as session_modes
from .state import SessionState, initialize_message_hex_ids


def switch_chat(
    state: SessionState,
    chat_path: str,
    chat_data: dict[str, Any],
    *,
    system_prompt_path: str | None,
) -> None:
    """Switch to a different chat and clear chat-scoped runtime state."""
    state.chat = chat_data
    state.chat_path = chat_path

    # Keep older chats aligned with active session system prompt metadata.
    metadata = chat_data.get("metadata") if isinstance(chat_data, dict) else None
    if isinstance(metadata, dict) and system_prompt_path and not metadata.get("system_prompt"):
        from ..chat import update_metadata

        update_metadata(chat_data, system_prompt=system_prompt_path)

    initialize_message_hex_ids(state)
    session_modes.clear_chat_scoped_state(state)


def close_chat(state: SessionState) -> None:
    """Close current chat and clear related runtime state."""
    state.chat = {}
    state.chat_path = None
    state.hex_id_set.clear()
    session_modes.clear_chat_scoped_state(state)

