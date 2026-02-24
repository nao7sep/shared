"""Chat list item formatting helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..constants import DATETIME_FORMAT_SHORT, DISPLAY_UNKNOWN


def _format_updated_time(updated_at: object) -> str:
    """Format ISO timestamp for chat list display."""
    if not isinstance(updated_at, str) or not updated_at:
        return str(DISPLAY_UNKNOWN)
    try:
        dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return str(dt.astimezone().strftime(DATETIME_FORMAT_SHORT))
    except Exception:
        return str(DISPLAY_UNKNOWN)


def format_chat_list_item(chat: dict[str, Any], index: int) -> str:
    """Format one chat record for interactive list display."""
    filename = str(chat.get("filename", DISPLAY_UNKNOWN))
    title = chat.get("title")
    msg_count = int(chat.get("message_count", 0) or 0)
    updated = _format_updated_time(chat.get("updated_at"))

    header = f"[{index}] {filename} | {msg_count} msgs | {updated}"
    if isinstance(title, str) and title.strip():
        return f"{header}\n    {title}"
    return header
