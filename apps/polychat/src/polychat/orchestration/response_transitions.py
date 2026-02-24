"""Transition policies for response/error/cancel orchestration flows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..orchestrator_types import ActionMode


@dataclass(slots=True, frozen=True)
class ResponseTransitionState:
    """Derived transition state used by response-mode handlers."""

    mode: ActionMode
    has_chat_context: bool
    has_assistant_hex_id: bool


def build_transition_state(
    mode: ActionMode,
    *,
    chat_path: str | None,
    chat_data: dict[str, Any] | None,
    assistant_hex_id: str | None,
) -> ResponseTransitionState:
    """Build derived state for response-mode transition decisions."""
    has_chat_context = bool(chat_path) and isinstance(chat_data, dict)
    has_assistant_hex_id = bool(assistant_hex_id)
    return ResponseTransitionState(
        mode=mode,
        has_chat_context=has_chat_context,
        has_assistant_hex_id=has_assistant_hex_id,
    )


def can_mutate_normal_chat(state: ResponseTransitionState) -> bool:
    """Return True when normal-mode chat mutations are valid."""
    return state.mode == "normal" and state.has_chat_context


def has_trailing_user_message(chat_data: dict[str, Any] | None) -> bool:
    """Return True when chat_data ends with a user message."""
    if not isinstance(chat_data, dict):
        return False
    messages = chat_data.get("messages")
    if not isinstance(messages, list) or not messages:
        return False
    tail = messages[-1]
    return isinstance(tail, dict) and tail.get("role") == "user"


def should_release_for_rollback(state: ResponseTransitionState) -> bool:
    """Rollback always releases reserved hex IDs when one exists."""
    return state.has_assistant_hex_id


def should_release_for_error(state: ResponseTransitionState) -> bool:
    """Return True when error handling should release reserved hex IDs."""
    if state.mode == "normal":
        return state.has_chat_context and state.has_assistant_hex_id
    return state.has_assistant_hex_id


def should_release_for_cancel(state: ResponseTransitionState) -> bool:
    """Return True when cancel handling should release reserved hex IDs."""
    if state.mode == "normal":
        return state.has_chat_context and state.has_assistant_hex_id
    return state.has_assistant_hex_id


def should_rollback_pre_send(
    state: ResponseTransitionState,
    chat_data: dict[str, Any] | None,
) -> bool:
    """Return True when pre-send rollback should mutate persisted chat state."""
    return can_mutate_normal_chat(state) and has_trailing_user_message(chat_data)
