"""Chat data management for PolyChat.

This module handles loading, saving, and manipulating chat history data,
including messages and metadata.
"""

import json
from copy import deepcopy
from pathlib import Path
from datetime import datetime, timezone
from typing import Any
import aiofiles

from .message_formatter import text_to_lines


REQUIRED_METADATA_KEYS = (
    "title",
    "summary",
    "system_prompt",
    "created_at",
    "updated_at",
)


def _normalize_metadata(raw_metadata: Any) -> dict[str, Any]:
    """Validate metadata shape and backfill missing known keys."""
    if not isinstance(raw_metadata, dict):
        raise ValueError("Invalid chat metadata: expected object")

    metadata = dict(raw_metadata)
    for key in REQUIRED_METADATA_KEYS:
        metadata.setdefault(key, None)
    return metadata


def _normalize_content(raw_content: Any) -> list[str]:
    """Normalize message content to list[str]."""
    if isinstance(raw_content, str):
        return text_to_lines(raw_content)
    if isinstance(raw_content, list):
        return [str(part) for part in raw_content]
    raise ValueError("Invalid message content: expected string or list")


def _normalize_messages(raw_messages: Any) -> list[dict[str, Any]]:
    """Validate message list and normalize content shape."""
    if not isinstance(raw_messages, list):
        raise ValueError("Invalid chat messages: expected list")

    normalized: list[dict[str, Any]] = []
    for index, raw_message in enumerate(raw_messages):
        if not isinstance(raw_message, dict):
            raise ValueError(f"Invalid chat message at index {index}: expected object")
        if "content" not in raw_message:
            raise ValueError(f"Invalid chat message at index {index}: missing content")

        message = dict(raw_message)
        message["content"] = _normalize_content(raw_message.get("content"))
        message.pop("hex_id", None)
        normalized.append(message)

    return normalized


def load_chat(path: str) -> dict[str, Any]:
    """Load chat history from JSON file.

    Args:
        path: Path to chat history file (already mapped)

    Returns:
        Chat dictionary (empty structure if file doesn't exist)

    Raises:
        ValueError: If JSON is invalid or structure is malformed
    """
    chat_path = Path(path)

    if not chat_path.exists():
        # Return empty chat structure
        return {
            "metadata": {
                "title": None,
                "summary": None,
                "system_prompt": None,
                "created_at": None,
                "updated_at": None,
            },
            "messages": [],
        }

    try:
        with open(chat_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            raise ValueError("Invalid chat history file structure")
        if "metadata" not in data or "messages" not in data:
            raise ValueError("Invalid chat history file structure")

        metadata = _normalize_metadata(data.get("metadata"))
        messages = _normalize_messages(data.get("messages"))

        return {"metadata": metadata, "messages": messages}

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in chat history file: {e}")


async def save_chat(path: str, data: dict[str, Any]) -> None:
    """Save chat history to JSON file (async).

    Args:
        path: Path to chat history file
        data: Chat dictionary

    Updates metadata.updated_at before saving.
    """
    # Update timestamp
    now = datetime.now(timezone.utc).isoformat()
    data["metadata"]["updated_at"] = now

    # If created_at not set, set it
    if not data["metadata"]["created_at"]:
        data["metadata"]["created_at"] = now

    # Ensure directory exists
    chat_path = Path(path)
    chat_path.parent.mkdir(parents=True, exist_ok=True)

    # Write async
    async with aiofiles.open(chat_path, "w", encoding="utf-8") as f:
        persistable_data = deepcopy(data)
        for message in persistable_data.get("messages", []):
            if isinstance(message, dict):
                message.pop("hex_id", None)

        # Use json.dumps first (it's not async), then write
        json_str = json.dumps(persistable_data, indent=2, ensure_ascii=False)
        await f.write(json_str)


def add_user_message(data: dict[str, Any], content: str) -> None:
    """Add user message to chat.

    Args:
        data: Chat dictionary
        content: Message text (multiline string)

    Formats content as line array with trimming.
    """
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
    thoughts: str | None = None,
) -> None:
    """Add assistant message to chat.

    Args:
        data: Chat dictionary
        content: Response text
        model: Model that generated the response
        citations: Optional list of source citations
        thoughts: Optional thinking/reasoning content
    """
    lines = text_to_lines(content)

    message = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "role": "assistant",
        "model": model,
        "content": lines,
    }
    if citations:
        message["citations"] = citations
    if thoughts:
        message["thoughts"] = thoughts

    data["messages"].append(message)


def add_error_message(
    data: dict[str, Any], content: str, details: dict[str, Any] | None = None
) -> None:
    """Add error message to chat.

    Args:
        data: Chat dictionary
        content: Error description
        details: Additional error information (optional)
    """
    lines = text_to_lines(content)

    message = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "role": "error",
        "content": lines,
    }

    if details:
        message["details"] = details

    data["messages"].append(message)


def delete_message_and_following(data: dict[str, Any], index: int) -> int:
    """Delete message at index and all following messages.

    Args:
        data: Chat dictionary
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
    """Update chat metadata.

    Args:
        data: Chat dictionary
        **kwargs: Metadata fields to update (title, summary, etc.)

    Example:
        update_metadata(chat, title="New Title", summary="...")
    """
    for key, value in kwargs.items():
        if key in data["metadata"]:
            data["metadata"][key] = value
        else:
            raise ValueError(f"Unknown metadata field: {key}")


def get_messages_for_ai(
    data: dict[str, Any], max_messages: int | None = None
) -> list[dict[str, Any]]:
    """Get messages formatted for AI (excluding error messages).

    Args:
        data: Chat dictionary
        max_messages: Maximum number of messages to return (from end)

    Returns:
        List of messages (user and assistant only)
    """
    # Filter out error messages
    messages = [msg for msg in data["messages"] if msg["role"] in ("user", "assistant")]

    # Limit if specified
    if max_messages is not None:
        messages = messages[-max_messages:]

    return messages
