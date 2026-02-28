"""Chat message mutation and query helpers."""

from __future__ import annotations

from typing import Any

from ..ai.types import Citation
from ..domain.chat import ChatDocument, ChatMessage


def add_user_message(data: ChatDocument, content: str) -> None:
    """Add user message to chat."""
    message = ChatMessage.new_user(content)
    data.messages.append(message)


def add_assistant_message(
    data: ChatDocument,
    content: str,
    model: str,
    citations: list[Citation] | None = None,
) -> None:
    """Add assistant message to chat."""
    message = ChatMessage.new_assistant(
        content,
        model=model,
        citations=citations,
    )
    data.messages.append(message)


def add_error_message(
    data: ChatDocument, content: str, details: dict[str, Any] | None = None
) -> None:
    """Add error message to chat."""
    message = ChatMessage.new_error(content, details=details)
    data.messages.append(message)


def delete_message_and_following(data: ChatDocument, index: int) -> int:
    """Delete message at index and all following messages."""
    messages = data.messages

    if index < 0 or index >= len(messages):
        raise IndexError(f"Message index {index} out of range")

    deleted_count = len(messages) - index
    data.messages = messages[:index]

    return deleted_count


def update_metadata(data: ChatDocument, **kwargs: object) -> None:
    """Update chat metadata."""
    for key, value in kwargs.items():
        if hasattr(data.metadata, key):
            setattr(data.metadata, key, value)
        else:
            raise ValueError(f"Unknown metadata field: {key}")


def get_messages_for_ai(
    data: ChatDocument, max_messages: int | None = None
) -> list[dict[str, Any]]:
    """Get messages formatted for AI (excluding error messages)."""
    messages = [msg.to_dict() for msg in data.messages if msg.role in ("user", "assistant")]

    if max_messages is not None:
        messages = messages[-max_messages:]

    return messages


def get_retry_context_for_last_interaction(data: ChatDocument) -> list[dict[str, Any]]:
    """Get retry context excluding the interaction currently being retried."""
    ai_messages = get_messages_for_ai(data)
    all_messages = data.messages

    if not all_messages or not ai_messages:
        return ai_messages

    last_role = all_messages[-1].role

    if last_role == "assistant":
        if (
            len(ai_messages) >= 2
            and ai_messages[-1].get("role") == "assistant"
            and ai_messages[-2].get("role") == "user"
        ):
            return ai_messages[:-2]
        if ai_messages[-1].get("role") == "assistant":
            return ai_messages[:-1]
        return ai_messages

    if last_role == "error" and ai_messages[-1].get("role") == "user":
        return ai_messages[:-1]

    return ai_messages
