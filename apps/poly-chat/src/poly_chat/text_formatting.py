"""Text formatting utilities for PolyChat."""

from datetime import datetime, timezone
from typing import Any, Callable
import re

from .constants import BORDERLINE_CHAR, BORDERLINE_WIDTH, DATETIME_FORMAT_SHORT


# ============================================================================
# Text Conversion
# ============================================================================

def text_to_lines(text: str) -> list[str]:
    """Convert multiline text to line array with trimming."""
    lines = text.split("\n")

    # Find first non-whitespace-only line.
    start = 0
    for i, line in enumerate(lines):
        if line.strip():
            start = i
            break
    else:
        return []

    # Find last non-whitespace-only line.
    end = len(lines)
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip():
            end = i + 1
            break

    return lines[start:end]


def lines_to_text(lines: list[str]) -> str:
    """Convert line array back to text."""
    return "\n".join(lines)


# ============================================================================
# String Utilities
# ============================================================================

def minify_text(text: str) -> str:
    """Collapse repeated whitespace to single spaces."""
    return re.sub(r"\s+", " ", text).strip()


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to max_length with suffix when needed."""
    if max_length <= 0:
        return ""

    if len(text) <= max_length:
        return text

    if len(suffix) >= max_length:
        return suffix[:max_length]

    return text[: max_length - len(suffix)] + suffix


# ============================================================================
# Borderline Formatting
# ============================================================================

def make_borderline(width: int | None = None, char: str | None = None) -> str:
    """Create a borderline."""
    return (char or BORDERLINE_CHAR) * (width or BORDERLINE_WIDTH)


def format_messages(
    messages: list[dict],
    message_formatter: Callable[[dict], str],
    borderline_width: int | None = None,
) -> str:
    """Format messages with borderlines using custom formatter."""
    borderline = make_borderline(borderline_width)
    parts = []

    for msg in messages:
        parts.append(borderline)
        parts.append(message_formatter(msg))

    parts.append(borderline)
    return "\n".join(parts)


# ============================================================================
# Message Formatting
# ============================================================================

def _get_content_text(msg: dict) -> str:
    """Extract content from message as text."""
    content = msg.get("content", [])
    if isinstance(content, list):
        return lines_to_text(content)
    return str(content)


def format_message_for_ai_context(msg: dict) -> str:
    """Format one message for AI context (title/summary generation)."""
    role = msg.get("role", "unknown")
    content = _get_content_text(msg)
    return f"{role}: {content}"


def format_message_for_safety_check(msg: dict) -> str:
    """Format one message for safety check."""
    role = msg.get("role", "unknown").upper()
    hex_id = msg.get("hex_id", "")
    content = _get_content_text(msg)
    hex_prefix = f"[{hex_id}] " if hex_id else ""
    return f"{hex_prefix}{role}: {content}"


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
        hex_id = msg.get("hex_id", "???")
        role = msg.get("role", "unknown")
        timestamp = msg.get("timestamp", "")

        if role == "user":
            role_display = "🍼 User"
        elif role == "assistant":
            model = msg.get("model", "unknown")
            role_display = f"🤖 Assistant/{model}"
        elif role == "error":
            role_display = "❌ Error"
        else:
            role_display = f"❓ {role.capitalize()}"

        if timestamp:
            time_str = timestamp_formatter(timestamp, DATETIME_FORMAT_SHORT)
            if time_str == "unknown":
                time_str = timestamp[:16] if len(timestamp) >= 16 else timestamp
        else:
            time_str = "unknown"

        content = msg.get("content", [])
        if isinstance(content, list):
            content_text = lines_to_text(content)
        else:
            content_text = str(content)
        content_preview = truncate_text(minify_text(content_text), truncate_length)

        header = f"[{hex_id}] {role_display} ({time_str})"
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


# ============================================================================
# Chat List Formatting
# ============================================================================

def _format_updated_time(updated_at: object) -> str:
    """Format ISO timestamp for chat list display."""
    if not isinstance(updated_at, str) or not updated_at:
        return "unknown"
    try:
        dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone().strftime(DATETIME_FORMAT_SHORT)
    except Exception:
        return "unknown"


def format_chat_list_item(chat: dict[str, Any], index: int) -> str:
    """Format one chat record for interactive list display."""
    filename = str(chat.get("filename", "(unknown)"))
    title = chat.get("title") or "(no title)"
    msg_count = int(chat.get("message_count", 0) or 0)
    updated = _format_updated_time(chat.get("updated_at"))

    header = f"[{index}] {filename} ({msg_count} msgs, {updated})"
    return f"{header}\n    {title}"


# ============================================================================
# Citation Formatting
# ============================================================================

def format_citation_item(citation: dict[str, Any], number: int) -> list[str]:
    """Format one citation record into display lines."""
    title = citation.get("title")
    url = citation.get("url")

    title_text = str(title) if title else ""
    url_text = str(url) if url else ""

    if title_text and url_text:
        return [f"  [{number}] {title_text}", f"      {url_text}"]
    if url_text:
        return [f"  [{number}] {url_text}"]
    if title_text:
        return [f"  [{number}] {title_text} (URL unavailable)"]
    return [f"  [{number}] [source unavailable]"]


def format_citation_list(citations: list[dict[str, Any]]) -> list[str]:
    """Format citations into printable lines."""
    if not citations:
        return []

    lines: list[str] = ["", "Sources:"]
    for i, citation in enumerate(citations, 1):
        number = citation.get("number", i)
        try:
            number_int = int(number)
        except Exception:
            number_int = i
        lines.extend(format_citation_item(citation, number_int))
    return lines
