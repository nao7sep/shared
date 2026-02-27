"""Message-history rendering and context formatting helpers."""

from __future__ import annotations

from typing import Callable

from .constants import (
    DATETIME_FORMAT_SHORT,
    DISPLAY_MISSING_HEX_ID,
    DISPLAY_UNKNOWN,
    EMOJI_ROLE_ASSISTANT,
    EMOJI_ROLE_ERROR,
    EMOJI_ROLE_UNKNOWN,
    EMOJI_ROLE_USER,
)
from .text import format_messages, lines_to_text, minify_text, truncate_text


def _get_content_text(msg: dict) -> str:
    """Extract content from message as text."""
    content = msg.get("content", [])
    if isinstance(content, list):
        return lines_to_text(content)
    return str(content)


def format_message_for_ai_context(msg: dict) -> str:
    """Format one message for AI context (title/summary generation)."""
    role = msg.get("role", DISPLAY_UNKNOWN)
    content = _get_content_text(msg)
    return f"{role}: {content}"


def format_message_for_safety_check(msg: dict) -> str:
    """Format one message for safety check."""
    return format_message_for_ai_context(msg)


def format_message_for_show(msg: dict) -> str:
    """Format one message for /show command (content only)."""
    return _get_content_text(msg)


def create_history_formatter(
    timestamp_formatter: Callable[[str, str], str],
    truncate_length: int = 100,
) -> Callable[[dict], str]:
    """Create a history message formatter with custom timestamp formatting."""

    def format_one_message(msg: dict) -> str:
        """Format one message for history display."""
        hex_id = msg.get("hex_id", DISPLAY_MISSING_HEX_ID)
        role = msg.get("role", DISPLAY_UNKNOWN)
        timestamp_utc = msg.get("timestamp_utc", "")

        if role == "user":
            role_display = f"{EMOJI_ROLE_USER} User"
        elif role == "assistant":
            model = msg.get("model", DISPLAY_UNKNOWN)
            role_display = f"{EMOJI_ROLE_ASSISTANT} Assistant | {model}"
        elif role == "error":
            role_display = f"{EMOJI_ROLE_ERROR} Error"
        else:
            role_display = f"{EMOJI_ROLE_UNKNOWN} {role.capitalize()}"

        if timestamp_utc:
            time_str = timestamp_formatter(timestamp_utc, DATETIME_FORMAT_SHORT)
        else:
            time_str = DISPLAY_UNKNOWN

        content = msg.get("content", [])
        if isinstance(content, list):
            content_text = lines_to_text(content)
        else:
            content_text = str(content)
        content_preview = truncate_text(minify_text(content_text), truncate_length)

        header = f"[{hex_id}] {role_display} | {time_str}"
        return f"{header}\n  {content_preview}"

    return format_one_message


def format_for_ai_context(messages: list[dict]) -> str:
    """Format messages for AI context (title/summary)."""
    return format_messages(messages, format_message_for_ai_context)


def format_for_safety_check(messages: list[dict]) -> str:
    """Format messages for safety check."""
    return format_messages(messages, format_message_for_safety_check)


def format_for_show(messages: list[dict]) -> str:
    """Format messages for /show."""
    return format_messages(messages, format_message_for_show)
