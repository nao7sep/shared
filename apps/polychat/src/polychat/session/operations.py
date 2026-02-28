"""Session operation helpers grouped by concern."""

from __future__ import annotations

from typing import Any, Optional

from ..domain.chat import ChatDocument, ChatMessage
from .state import SessionState, initialize_message_hex_ids


# ===================================================================
# Chat lifecycle
# ===================================================================


def switch_chat(
    state: SessionState,
    chat_path: str,
    chat_data: ChatDocument,
    *,
    system_prompt_path: str | None,
) -> None:
    """Switch to a different chat and clear chat-scoped runtime state."""
    state.chat = chat_data
    state.chat_path = chat_path

    # Keep older chats aligned with active session system prompt metadata.
    if system_prompt_path and not chat_data.metadata.system_prompt:
        from ..chat import update_metadata

        update_metadata(chat_data, system_prompt=system_prompt_path)

    initialize_message_hex_ids(state)
    clear_chat_scoped_state(state)


def close_chat(state: SessionState) -> None:
    """Close current chat and clear related runtime state."""
    state.chat = ChatDocument.empty()
    state.chat_path = None
    state.hex_id_set.clear()
    clear_chat_scoped_state(state)


# ===================================================================
# Mode transitions
# ===================================================================


def clear_chat_scoped_state(state: SessionState) -> None:
    """Clear state that should not leak across chat boundaries."""
    state.retry.clear()
    state.secret.clear()
    state.search_mode = False


# ===================================================================
# Message-level hex-id helpers
# ===================================================================


def get_message_hex_id(state: SessionState, message_index: int) -> Optional[str]:
    """Get hex ID for a message index."""
    messages = state.chat.messages
    if message_index < 0 or message_index >= len(messages):
        return None
    hid = messages[message_index].hex_id
    return hid if isinstance(hid, str) else None


def remove_message_hex_id(state: SessionState, message_index: int) -> None:
    """Remove hex ID for a message index."""
    messages = state.chat.messages
    if message_index < 0 or message_index >= len(messages):
        return
    hex_to_remove = messages[message_index].hex_id
    messages[message_index].hex_id = None
    if isinstance(hex_to_remove, str):
        state.hex_id_set.discard(hex_to_remove)


def pop_message(
    state: SessionState,
    message_index: int = -1,
    chat_data: Optional[ChatDocument] = None,
) -> Optional[ChatMessage]:
    """Pop a message and atomically clean up its runtime hex ID."""
    target_chat = chat_data if chat_data is not None else state.chat

    messages = target_chat.messages
    if not messages:
        return None

    popped = messages.pop(message_index)
    hex_to_remove = popped.hex_id
    popped.hex_id = None
    if isinstance(hex_to_remove, str):
        state.hex_id_set.discard(hex_to_remove)
    return popped


# ===================================================================
# Persistence and provider cache
# ===================================================================


async def save_current_chat(
    state: SessionState,
    *,
    chat_path: Optional[str] = None,
    chat_data: Optional[ChatDocument] = None,
) -> bool:
    """Persist current chat state.

    Returns True when a save was performed, False when skipped.
    """
    path = chat_path if chat_path is not None else state.chat_path
    data = chat_data if chat_data is not None else state.chat

    if not path or data is None:
        return False

    from .. import chat as chat_module

    await chat_module.save_chat(path, data)
    return True


def get_cached_provider(
    state: SessionState,
    provider_name: str,
    api_key: str,
    timeout_sec: int | float | None = None,
) -> Optional[Any]:
    """Get cached provider instance."""
    return state.get_cached_provider(provider_name, api_key, timeout_sec=timeout_sec)


def cache_provider(
    state: SessionState,
    provider_name: str,
    api_key: str,
    instance: Any,
    timeout_sec: int | float | None = None,
) -> None:
    """Cache provider instance."""
    state.cache_provider(provider_name, api_key, instance, timeout_sec=timeout_sec)


def clear_provider_cache(state: SessionState) -> None:
    """Clear all cached provider instances."""
    state.clear_provider_cache()


# ===================================================================
# Runtime settings helpers
# ===================================================================


def switch_provider(state: SessionState, provider_name: str, model_name: str) -> None:
    """Switch active provider/model pair."""
    state.current_ai = provider_name
    state.current_model = model_name


def toggle_input_mode(state: SessionState) -> str:
    """Toggle input mode between quick and compose."""
    if state.input_mode == "quick":
        state.input_mode = "compose"
    else:
        state.input_mode = "quick"
    return state.input_mode
