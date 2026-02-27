"""Chat document storage and normalization helpers."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import aiofiles  # type: ignore[import-untyped]

from ..domain.chat import REQUIRED_METADATA_KEYS as DOMAIN_REQUIRED_METADATA_KEYS, ChatDocument

REQUIRED_METADATA_KEYS = DOMAIN_REQUIRED_METADATA_KEYS


def _canonical_for_change_detection(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize payload for no-op save detection."""
    normalized = copy.deepcopy(payload)
    metadata = normalized.get("metadata")
    if isinstance(metadata, dict):
        metadata["updated_utc"] = None
    return normalized


def _load_existing_persistable_chat(chat_path: Path) -> dict[str, Any] | None:
    """Load and normalize existing persisted chat for change detection."""
    if not chat_path.exists():
        return None

    try:
        with open(chat_path, "r", encoding="utf-8") as f:
            raw: Any = json.load(f)
        document = ChatDocument.from_raw(raw, strip_runtime_hex_id=True)
        return document.to_dict(include_runtime_hex_id=False)
    except Exception:
        # Fall back to writing a fresh valid payload.
        return None


def _sync_in_memory_metadata(data: dict[str, Any], metadata: dict[str, Any]) -> None:
    """Mirror persisted created/updated timestamps into in-memory chat data."""
    target = data.get("metadata")
    if isinstance(target, dict):
        target["created_utc"] = metadata.get("created_utc")
        target["updated_utc"] = metadata.get("updated_utc")


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
    chat_path = Path(path)
    document = ChatDocument.from_raw(data, strip_runtime_hex_id=False)
    persistable_data = document.to_dict(include_runtime_hex_id=False)
    existing_data = _load_existing_persistable_chat(chat_path)

    if existing_data is not None and _canonical_for_change_detection(
        persistable_data
    ) == _canonical_for_change_detection(existing_data):
        existing_metadata = existing_data.get("metadata")
        if isinstance(existing_metadata, dict):
            _sync_in_memory_metadata(data, existing_metadata)
        return

    document.touch_updated_utc()
    persistable_data = document.to_dict(include_runtime_hex_id=False)
    _sync_in_memory_metadata(data, document.metadata.to_dict())

    chat_path.parent.mkdir(parents=True, exist_ok=True)

    async with aiofiles.open(chat_path, "w", encoding="utf-8") as f:
        json_str = json.dumps(persistable_data, indent=2, ensure_ascii=False)
        await f.write(json_str)
