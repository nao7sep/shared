"""Backward-compatible facade for session state APIs."""

from .session.state import (
    SessionState,
    assign_new_message_hex_id,
    has_pending_error,
    initialize_message_hex_ids,
    pending_error_guidance,
)

__all__ = [
    "SessionState",
    "initialize_message_hex_ids",
    "assign_new_message_hex_id",
    "has_pending_error",
    "pending_error_guidance",
]

