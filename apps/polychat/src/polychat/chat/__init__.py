"""Chat domain package: storage and message helpers."""

from .messages import (
    add_assistant_message,
    add_error_message,
    add_user_message,
    delete_message_and_following,
    get_messages_for_ai,
    get_retry_context_for_last_interaction,
    update_metadata,
)
from .storage import REQUIRED_METADATA_KEYS, load_chat, save_chat

__all__ = [
    "REQUIRED_METADATA_KEYS",
    "load_chat",
    "save_chat",
    "add_user_message",
    "add_assistant_message",
    "add_error_message",
    "delete_message_and_following",
    "update_metadata",
    "get_messages_for_ai",
    "get_retry_context_for_last_interaction",
]

