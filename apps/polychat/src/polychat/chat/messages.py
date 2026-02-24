"""Chat message mutation and query helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..formatting.text import text_to_lines


def add_user_message(data: dict[str, Any], content: str) -> None:
    """Add user message to chat."""
    lines = text_to_lines(content)

    message = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "role": "user",
        "content": lines,
    }

    data["messages"].append(message)


def add_assistant_message(
    data: dict[str, Any],
    content: str,
    model: str,
    citations: list[dict[str, Any]] | None = None,
) -> None:
    """Add assistant message to chat."""
    lines = text_to_lines(content)

    message: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "role": "assistant",
        "model": model,
        "content": lines,
    }
    if citations:
        message["citations"] = citations

    data["messages"].append(message)


def add_error_message(
    data: dict[str, Any], content: str, details: dict[str, Any] | None = None
) -> None:
    """Add error message to chat."""
    lines = text_to_lines(content)

    message: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "role": "error",
        "content": lines,
    }

    if details:
        message["details"] = details

    data["messages"].append(message)


def delete_message_and_following(data: dict[str, Any], index: int) -> int:
    """Delete message at index and all following messages."""
    messages = data["messages"]

    if index < 0 or index >= len(messages):
        raise IndexError(f"Message index {index} out of range")

    deleted_count = len(messages) - index
    data["messages"] = messages[:index]

    return deleted_count


def update_metadata(data: dict[str, Any], **kwargs: object) -> None:
    """Update chat metadata."""
    for key, value in kwargs.items():
        if key in data["metadata"]:
            data["metadata"][key] = value
        else:
            raise ValueError(f"Unknown metadata field: {key}")


def get_messages_for_ai(
    data: dict[str, Any], max_messages: int | None = None
) -> list[dict[str, Any]]:
    """Get messages formatted for AI (excluding error messages)."""
    messages = [msg for msg in data["messages"] if msg["role"] in ("user", "assistant")]

    if max_messages is not None:
        messages = messages[-max_messages:]

    return messages


def get_retry_context_for_last_interaction(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Get retry context excluding the interaction currently being retried."""
    ai_messages = get_messages_for_ai(data)
    all_messages = data.get("messages", []) if isinstance(data, dict) else []

    if not all_messages or not ai_messages:
        return ai_messages

    last_role = all_messages[-1].get("role")

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
