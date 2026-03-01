"""Chat domain package: storage and message helpers."""

from .messages import (
    LastInteractionSpan,
    add_assistant_message,
    add_error_message,
    add_user_message,
    delete_message_and_following,
    filter_messages_for_ai,
    get_messages_for_ai,
    get_retry_context_for_last_interaction,
    resolve_last_interaction_span,
    update_metadata,
)
from .storage import REQUIRED_METADATA_KEYS, load_chat, save_chat

__all__ = [
    "REQUIRED_METADATA_KEYS",
    "load_chat",
    "save_chat",
    "LastInteractionSpan",
    "add_user_message",
    "add_assistant_message",
    "add_error_message",
    "delete_message_and_following",
    "update_metadata",
    "filter_messages_for_ai",
    "get_messages_for_ai",
    "get_retry_context_for_last_interaction",
    "resolve_last_interaction_span",
]
