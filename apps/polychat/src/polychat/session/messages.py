"""Message-level hex-id helpers for session state."""

from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..app_state import SessionState


def get_message_hex_id(state: "SessionState", message_index: int) -> Optional[str]:
    """Get hex ID for a message index."""
    messages = state.chat.get("messages", []) if isinstance(state.chat, dict) else []
    if message_index < 0 or message_index >= len(messages):
        return None
    hid = messages[message_index].get("hex_id")
    return hid if isinstance(hid, str) else None


def remove_message_hex_id(state: "SessionState", message_index: int) -> None:
    """Remove hex ID for a message index."""
    messages = state.chat.get("messages", []) if isinstance(state.chat, dict) else []
    if message_index < 0 or message_index >= len(messages):
        return
    hex_to_remove = messages[message_index].pop("hex_id", None)
    if isinstance(hex_to_remove, str):
        state.hex_id_set.discard(hex_to_remove)


def pop_message(
    state: "SessionState",
    message_index: int = -1,
    chat_data: Optional[dict[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    """Pop a message and atomically clean up its runtime hex ID."""
    target_chat = chat_data if chat_data is not None else state.chat
    if not isinstance(target_chat, dict):
        return None

    messages = target_chat.get("messages")
    if not isinstance(messages, list) or not messages:
        return None

    popped = messages.pop(message_index)
    if isinstance(popped, dict):
        hex_to_remove = popped.pop("hex_id", None)
        if isinstance(hex_to_remove, str):
            state.hex_id_set.discard(hex_to_remove)
    return popped if isinstance(popped, dict) else None
