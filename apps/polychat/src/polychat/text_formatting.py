"""Text formatting utilities for PolyChat."""

from datetime import datetime, timezone
from typing import Any, Callable
import unicodedata
import re

from .constants import (
    BORDERLINE_CHAR,
    BORDERLINE_WIDTH,
    DATETIME_FORMAT_SHORT,
    DISPLAY_MISSING_HEX_ID,
    DISPLAY_UNKNOWN,
    EMOJI_ROLE_ASSISTANT,
    EMOJI_ROLE_ERROR,
    EMOJI_ROLE_UNKNOWN,
    EMOJI_ROLE_USER,
    TRUNCATE_SEARCH_RADIUS,
)


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


def _is_truncate_boundary(character: str) -> bool:
    """Return True when character is a Unicode separator or punctuation.
    
    Uses Unicode categories to identify good truncation boundaries:
    - Z* categories (separators): spaces, line breaks, paragraph breaks
      - Zs: Space Separator (regular space, non-breaking space, etc.)
      - Zl: Line Separator
      - Zp: Paragraph Separator
    - P* categories (punctuation): periods, commas, colons, etc.
      - Pc: Connector Punctuation (underscore, etc.)
      - Pd: Dash Punctuation (hyphen, em dash, etc.)
      - Ps: Open Punctuation (opening bracket, paren, etc.)
      - Pe: Close Punctuation (closing bracket, paren, etc.)
      - Pi: Initial Punctuation (opening quote, etc.)
      - Pf: Final Punctuation (closing quote, etc.)
      - Po: Other Punctuation (period, comma, colon, etc.)
    
    These are good places to truncate text because breaking at
    separators/punctuation maintains readability.
    """
    return bool(character) and unicodedata.category(character).startswith(("Z", "P"))


def _find_truncate_position(text: str, target: int, search_radius: int) -> int | None:
    """Find the best position to truncate text near the target.
    
    Searches backward from target within search_radius for a word boundary.
    When found, rewinds past any trailing boundaries to avoid cutting at
    "word... " (returns position after "word").
    
    Args:
        text: Text to search in
        target: Ideal truncation position
        search_radius: How far to search backward from target
        
    Returns:
        Best truncation position, or None if no good boundary found
        
    Example:
        text = "Hello world, this is neat"
        target = 15  # Points to 'i' in "this"
        search_radius = 5
        # Searches positions 10-15, finds space at 12
        # Rewinds past comma at 11 (also a boundary)
        # Returns 11 (cuts at "Hello world", comma removed)
    """
    search_start = max(0, target - search_radius)
    
    for pos in range(target, search_start - 1, -1):
        if pos < len(text) and _is_truncate_boundary(text[pos]):
            # Found a boundary! Rewind past any trailing boundaries
            # This handles "word,  " -> cuts at "word"
            while pos > 0 and _is_truncate_boundary(text[pos - 1]):
                pos -= 1
            return pos if pos > 0 else None
    
    return None


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to max_length, preferring to break at word boundaries.
    
    Strategy:
    1. If text fits, return as-is
    2. Calculate target position (max_length - suffix length)
    3. Search backward within radius for a word boundary
    4. If found, break there (after stripping trailing boundaries)
    5. If not found, break exactly at target
    6. Add suffix
    
    Args:
        text: Text to truncate
        max_length: Maximum length including suffix
        suffix: String to append when truncating (default "...")
        
    Returns:
        Truncated text with suffix, or original text if it fits
        
    Examples:
        >>> truncate_text("Hello world", 100)
        "Hello world"
        
        >>> truncate_text("Hello world this is long", 15)
        "Hello world..."
        
        >>> truncate_text("NoSpacesHereAtAll", 10)
        "NoSpace..."
    """
    if max_length <= 0:
        return ""

    if len(text) <= max_length:
        return text

    if len(suffix) >= max_length:
        return suffix[:max_length]

    target = max_length - len(suffix)
    
    # Try to find a good break point near target
    break_pos = _find_truncate_position(text, target, TRUNCATE_SEARCH_RADIUS)
    
    if break_pos is not None:
        # Found a good boundary
        truncated = text[:break_pos].rstrip()
    else:
        # No good boundary found, break at target
        truncated = text[:target].rstrip()
    
    # Edge case: if rstrip removed everything, use target without stripping
    if not truncated:
        truncated = text[:target]
    
    return truncated + suffix


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
        timestamp = msg.get("timestamp", "")

        if role == "user":
            role_display = f"{EMOJI_ROLE_USER} User"
        elif role == "assistant":
            model = msg.get("model", DISPLAY_UNKNOWN)
            role_display = f"{EMOJI_ROLE_ASSISTANT} Assistant | {model}"
        elif role == "error":
            role_display = f"{EMOJI_ROLE_ERROR} Error"
        else:
            role_display = f"{EMOJI_ROLE_UNKNOWN} {role.capitalize()}"

        if timestamp:
            time_str = timestamp_formatter(timestamp, DATETIME_FORMAT_SHORT)
            # If formatter returns DISPLAY_UNKNOWN, keep it as is
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


# ============================================================================
# Chat List Formatting
# ============================================================================

def _format_updated_time(updated_at: object) -> str:
    """Format ISO timestamp for chat list display."""
    if not isinstance(updated_at, str) or not updated_at:
        return DISPLAY_UNKNOWN
    try:
        dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone().strftime(DATETIME_FORMAT_SHORT)
    except Exception:
        return DISPLAY_UNKNOWN


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
