"""Conversation data management for PolyChat.

This module handles loading, saving, and manipulating conversation data,
including messages and metadata.
"""

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Any
import aiofiles

from .message_formatter import text_to_lines


def load_conversation(path: str) -> dict[str, Any]:
    """Load conversation from JSON file.

    Args:
        path: Path to conversation file (already mapped)

    Returns:
        Conversation dictionary

    Raises:
        FileNotFoundError: If file doesn't exist (caller should create new)
        ValueError: If JSON is invalid
    """
    conv_path = Path(path)

    if not conv_path.exists():
        # Return empty conversation structure
        return {
            "metadata": {
                "title": None,
                "summary": None,
                "system_prompt_key": None,
                "default_model": None,
                "created_at": None,
                "updated_at": None
            },
            "messages": []
        }

    try:
        with open(conv_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Validate structure
        if "metadata" not in data or "messages" not in data:
            raise ValueError("Invalid conversation file structure")

        return data

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in conversation file: {e}")


async def save_conversation(path: str, data: dict[str, Any]) -> None:
    """Save conversation to JSON file (async).

    Args:
        path: Path to conversation file
        data: Conversation dictionary

    Updates metadata.updated_at before saving.
    """
    # Update timestamp
    now = datetime.now(timezone.utc).isoformat()
    data["metadata"]["updated_at"] = now

    # If created_at not set, set it
    if not data["metadata"]["created_at"]:
        data["metadata"]["created_at"] = now

    # Ensure directory exists
    conv_path = Path(path)
    conv_path.parent.mkdir(parents=True, exist_ok=True)

    # Write async
    async with aiofiles.open(conv_path, "w", encoding="utf-8") as f:
        # Use json.dumps first (it's not async), then write
        json_str = json.dumps(data, indent=2, ensure_ascii=False)
        await f.write(json_str)


def add_user_message(data: dict[str, Any], content: str) -> None:
    """Add user message to conversation.

    Args:
        data: Conversation dictionary
        content: Message text (multiline string)

    Formats content as line array with trimming.
    """
    lines = text_to_lines(content)

    message = {
        "role": "user",
        "content": lines,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    data["messages"].append(message)


def add_assistant_message(
    data: dict[str, Any],
    content: str,
    model: str
) -> None:
    """Add assistant message to conversation.

    Args:
        data: Conversation dictionary
        content: Response text
        model: Model that generated the response
    """
    lines = text_to_lines(content)

    message = {
        "role": "assistant",
        "content": lines,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": model
    }

    data["messages"].append(message)


def add_error_message(
    data: dict[str, Any],
    content: str,
    details: dict[str, Any] | None = None
) -> None:
    """Add error message to conversation.

    Args:
        data: Conversation dictionary
        content: Error description
        details: Additional error information (optional)
    """
    lines = text_to_lines(content)

    message = {
        "role": "error",
        "content": lines,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    if details:
        message["details"] = details

    data["messages"].append(message)


def delete_message_and_following(data: dict[str, Any], index: int) -> int:
    """Delete message at index and all following messages.

    Args:
        data: Conversation dictionary
        index: Index of message to delete (0-based)

    Returns:
        Number of messages deleted

    Raises:
        IndexError: If index out of range
    """
    messages = data["messages"]

    if index < 0 or index >= len(messages):
        raise IndexError(f"Message index {index} out of range")

    deleted_count = len(messages) - index
    data["messages"] = messages[:index]

    return deleted_count


def update_metadata(data: dict[str, Any], **kwargs) -> None:
    """Update conversation metadata.

    Args:
        data: Conversation dictionary
        **kwargs: Metadata fields to update (title, summary, etc.)

    Example:
        update_metadata(conv, title="New Title", summary="...")
    """
    for key, value in kwargs.items():
        if key in data["metadata"]:
            data["metadata"][key] = value
        else:
            raise ValueError(f"Unknown metadata field: {key}")


def get_messages_for_ai(
    data: dict[str, Any],
    max_messages: int | None = None
) -> list[dict[str, Any]]:
    """Get messages formatted for AI (excluding error messages).

    Args:
        data: Conversation dictionary
        max_messages: Maximum number of messages to return (from end)

    Returns:
        List of messages (user and assistant only)
    """
    # Filter out error messages
    messages = [
        msg for msg in data["messages"]
        if msg["role"] in ("user", "assistant")
    ]

    # Limit if specified
    if max_messages is not None:
        messages = messages[-max_messages:]

    return messages
