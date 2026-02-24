"""Chat document storage and normalization helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import aiofiles  # type: ignore[import-untyped]

from ..domain.chat import REQUIRED_METADATA_KEYS as DOMAIN_REQUIRED_METADATA_KEYS, ChatDocument

REQUIRED_METADATA_KEYS = DOMAIN_REQUIRED_METADATA_KEYS


def load_chat(path: str) -> dict[str, Any]:
    """Load chat history from JSON file."""
    chat_path = Path(path)

    if not chat_path.exists():
        return ChatDocument.empty().to_dict()

    try:
        with open(chat_path, "r", encoding="utf-8") as f:
            data: Any = json.load(f)

        document = ChatDocument.from_raw(data, strip_runtime_hex_id=True)
        return document.to_dict(include_runtime_hex_id=False)

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in chat history file: {e}")


async def save_chat(path: str, data: dict[str, Any]) -> None:
    """Save chat history to JSON file (async)."""
    document = ChatDocument.from_raw(data, strip_runtime_hex_id=False)
    document.touch_updated_at()

    if isinstance(data.get("metadata"), dict):
        data["metadata"]["updated_at"] = document.metadata.updated_at
        data["metadata"]["created_at"] = document.metadata.created_at

    chat_path = Path(path)
    chat_path.parent.mkdir(parents=True, exist_ok=True)

    async with aiofiles.open(chat_path, "w", encoding="utf-8") as f:
        persistable_data = document.to_dict(include_runtime_hex_id=False)
        json_str = json.dumps(persistable_data, indent=2, ensure_ascii=False)
        await f.write(json_str)
