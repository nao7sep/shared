"""Chat list item formatting helpers."""

from __future__ import annotations

from ..domain.chat import ChatListEntry
from ..time_utils import parse_utc_to_local
from .constants import DATETIME_FORMAT_SHORT, DISPLAY_UNKNOWN


def _format_updated_time(updated_utc: object) -> str:
    """Format ISO timestamp for chat list display."""
    if not isinstance(updated_utc, str) or not updated_utc:
        return str(DISPLAY_UNKNOWN)
    return parse_utc_to_local(updated_utc, DATETIME_FORMAT_SHORT) or str(DISPLAY_UNKNOWN)


def format_chat_list_item(chat: ChatListEntry, index: int, width: int = 1) -> str:
    """Format one chat record for interactive list display.

    Args:
        chat: Chat list entry data.
        index: 1-based position in the list.
        width: Minimum digit width for left-padding the index so columns align.
    """
    filename = chat.filename
    title = chat.title
    msg_count = chat.message_count
    updated = _format_updated_time(chat.updated_utc)

    indent = " " * (width + 3)
    header = f"[{index:>{width}}] {filename} | {msg_count} msgs | {updated}"
    if isinstance(title, str) and title.strip():
        return f"{header}\n{indent}{title}"
    return header
