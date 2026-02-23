"""Retry/secret/search mode state transitions for session state."""

from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING

from .. import hex_id

if TYPE_CHECKING:
    from ..app_state import SessionState


def clear_chat_scoped_state(state: "SessionState") -> None:
    """Clear state that should not leak across chat boundaries."""
    # Clear retry mode.
    state.retry_mode = False
    state.retry_base_messages.clear()
    state.retry_target_index = None
    for hid in list(state.retry_attempts.keys()):
        state.hex_id_set.discard(hid)
    state.retry_attempts.clear()

    # Clear secret mode.
    state.secret_mode = False
    state.secret_base_messages.clear()

    # Clear search mode.
    state.search_mode = False


def enter_retry_mode(
    state: "SessionState",
    base_messages: list[dict],
    target_index: int | None = None,
) -> None:
    """Enter retry mode with frozen message context."""
    if state.secret_mode:
        raise ValueError("Cannot enter retry mode while in secret mode")

    state.retry_mode = True
    state.retry_base_messages = base_messages.copy()
    state.retry_target_index = target_index
    for hid in list(state.retry_attempts.keys()):
        state.hex_id_set.discard(hid)
    state.retry_attempts.clear()


def get_retry_context(state: "SessionState") -> list[dict]:
    """Return frozen retry context."""
    if not state.retry_mode:
        raise ValueError("Not in retry mode")
    return state.retry_base_messages


def add_retry_attempt(
    state: "SessionState",
    user_msg: str,
    assistant_msg: str,
    retry_hex_id: Optional[str] = None,
    citations: Optional[list[dict[str, Any]]] = None,
) -> str:
    """Store a retry attempt and return its runtime hex ID."""
    if not state.retry_mode:
        raise ValueError("Not in retry mode")

    if retry_hex_id is None:
        retry_hex_id = hex_id.generate_hex_id(state.hex_id_set)
    else:
        state.hex_id_set.add(retry_hex_id)
    state.retry_attempts[retry_hex_id] = {
        "user_msg": user_msg,
        "assistant_msg": assistant_msg,
    }
    if citations:
        state.retry_attempts[retry_hex_id]["citations"] = citations
    return retry_hex_id


def get_retry_attempt(
    state: "SessionState",
    retry_hex_id: str,
) -> Optional[dict[str, Any]]:
    """Get one retry attempt by runtime hex ID."""
    return state.retry_attempts.get(retry_hex_id)


def get_latest_retry_attempt_id(state: "SessionState") -> Optional[str]:
    """Return most recently generated retry attempt hex ID."""
    if not state.retry_attempts:
        return None
    return next(reversed(state.retry_attempts))


def get_retry_target_index(state: "SessionState") -> Optional[int]:
    """Return the target index used by /apply replacement."""
    return state.retry_target_index


def reserve_hex_id(state: "SessionState") -> str:
    """Reserve a runtime hex ID for an in-flight assistant response."""
    return hex_id.generate_hex_id(state.hex_id_set)


def release_hex_id(state: "SessionState", message_hex_id: str) -> None:
    """Release a reserved runtime hex ID."""
    state.hex_id_set.discard(message_hex_id)


def exit_retry_mode(state: "SessionState") -> None:
    """Exit retry mode and clear retry state."""
    state.retry_mode = False
    state.retry_base_messages.clear()
    state.retry_target_index = None
    for hid in list(state.retry_attempts.keys()):
        state.hex_id_set.discard(hid)
    state.retry_attempts.clear()


def enter_secret_mode(state: "SessionState", base_messages: list[dict]) -> None:
    """Enter secret mode and store context snapshot."""
    if state.retry_mode:
        raise ValueError("Cannot enter secret mode while in retry mode")

    state.secret_mode = True
    state.secret_base_messages = base_messages.copy()


def get_secret_context(state: "SessionState") -> list[dict]:
    """Return secret-mode context snapshot."""
    if not state.secret_mode:
        raise ValueError("Not in secret mode")
    return state.secret_base_messages


def exit_secret_mode(state: "SessionState") -> None:
    """Exit secret mode and clear secret state."""
    state.secret_mode = False
    state.secret_base_messages.clear()
