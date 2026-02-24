"""Chat document storage and normalization helpers."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiofiles  # type: ignore[import-untyped]

from ..formatting.text import text_to_lines


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
    """Load chat history from JSON file."""
    chat_path = Path(path)

    if not chat_path.exists():
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
    """Save chat history to JSON file (async)."""
    now = datetime.now(timezone.utc).isoformat()
    data["metadata"]["updated_at"] = now

    if not data["metadata"]["created_at"]:
        data["metadata"]["created_at"] = now

    chat_path = Path(path)
    chat_path.parent.mkdir(parents=True, exist_ok=True)

    async with aiofiles.open(chat_path, "w", encoding="utf-8") as f:
        persistable_data = deepcopy(data)
        for message in persistable_data.get("messages", []):
            if isinstance(message, dict):
                message.pop("hex_id", None)

        json_str = json.dumps(persistable_data, indent=2, ensure_ascii=False)
        await f.write(json_str)
