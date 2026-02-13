"""Message formatting utilities for PolyChat.

This module handles conversion between multiline text and line arrays,
with proper trimming of leading/trailing whitespace-only lines while
preserving empty lines within content.

It also provides formatters for displaying messages in various contexts.
"""

import re
from typing import Callable


# ============================================================================
# Basic text conversion
# ============================================================================

def text_to_lines(text: str) -> list[str]:
    """Convert multiline text to line array with trimming.

    Args:
        text: Input text (may have leading/trailing whitespace-only lines)

    Returns:
        List of lines with leading/trailing whitespace-only lines removed

    Algorithm:
    1. Split by \n
    2. Find first non-whitespace-only line
    3. Find last non-whitespace-only line
    4. Return lines in that range
    5. Preserve empty lines within content as ""

    Example:
        Input: "\n\nFirst line\n\nSecond line\n\n"
        Output: ["First line", "", "Second line"]
    """
    lines = text.split("\n")

    # Find first non-whitespace-only line
    start = 0
    for i, line in enumerate(lines):
        if line.strip():  # Has non-whitespace content
            start = i
            break
    else:
        # All lines are whitespace-only
        return []

    # Find last non-whitespace-only line
    end = len(lines)
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip():
            end = i + 1
            break

    return lines[start:end]


def lines_to_text(lines: list[str]) -> str:
    """Convert line array back to text.

    Args:
        lines: List of lines

    Returns:
        Joined text with \n
    """
    return "\n".join(lines)


# ============================================================================
# Core formatting function
# ============================================================================

def format_messages(
    messages: list[dict],
    message_formatter: Callable[[dict], str],
    separator_width: int = 60,
) -> str:
    """Format messages with separators using custom formatter.

    Args:
        messages: List of message dicts (can be empty)
        message_formatter: Function that converts one message dict → one string
        separator_width: Width of separator lines

    Returns:
        Formatted string with separators between messages

    Example:
        def my_formatter(msg):
            return f"{msg['role']}: {msg['content']}"

        result = format_messages(messages, my_formatter)
    """
    separator = "━" * separator_width
    parts = []

    for msg in messages:
        parts.append(separator)
        parts.append(message_formatter(msg))

    parts.append(separator)
    return "\n".join(parts)


# ============================================================================
# Utility functions
# ============================================================================

def _get_content_text(msg: dict) -> str:
    """Extract content from message as text."""
    content = msg.get("content", [])
    if isinstance(content, list):
        return lines_to_text(content)
    return str(content)


def minify_and_truncate(content: str | list[str], max_length: int) -> str:
    """Minify whitespace and truncate content for preview display.

    Args:
        content: Message content as string or list of lines
        max_length: Maximum length before truncation

    Returns:
        Minified and truncated string with "..." if truncated

    Minification collapses all whitespace (spaces, newlines, tabs) into single spaces.
    """
    # Convert to text if needed
    if isinstance(content, list):
        content_text = lines_to_text(content)
    else:
        content_text = str(content)

    # Collapse all whitespace to single spaces
    minified = re.sub(r'\s+', ' ', content_text).strip()

    # Truncate if needed
    if len(minified) > max_length:
        return minified[:max_length - 3] + "..."

    return minified


# ============================================================================
# Built-in message formatters
# ============================================================================

def format_message_for_ai_context(msg: dict) -> str:
    """Format one message for AI context (title/summary generation).

    Args:
        msg: Message dict with 'role' and 'content'

    Returns:
        Formatted string: "role: content"
    """
    role = msg.get("role", "unknown")
    content = _get_content_text(msg)
    return f"{role}: {content}"


def format_message_for_safety_check(msg: dict) -> str:
    """Format one message for safety check.

    Args:
        msg: Message dict with 'role', 'hex_id', and 'content'

    Returns:
        Formatted string: "[hex_id] ROLE: content"
    """
    role = msg.get("role", "unknown").upper()
    hex_id = msg.get("hex_id", "")
    content = _get_content_text(msg)
    hex_prefix = f"[{hex_id}] " if hex_id else ""
    return f"{hex_prefix}{role}: {content}"


def format_message_for_show(msg: dict) -> str:
    """Format one message for /show command (content only).

    Args:
        msg: Message dict with 'content'

    Returns:
        Formatted string: "content"
    """
    return _get_content_text(msg)


def create_history_formatter(
    timestamp_formatter: Callable[[str, str], str],
    truncate_length: int = 100,
) -> Callable[[dict], str]:
    """Create a history message formatter with custom timestamp formatting.

    Args:
        timestamp_formatter: Function (timestamp, format_str) -> formatted_string
        truncate_length: Max content length before truncation

    Returns:
        Message formatter function for /history display

    Example:
        formatter = create_history_formatter(self._to_local_time, 100)
        formatted = format_messages(messages, formatter, 60)
    """
    def format_one_message(msg: dict) -> str:
        """Format one message for history display.

        Returns: "[hex] 👤 Role (time)\n  content..."
        """
        hex_id = msg.get("hex_id", "???")
        role = msg.get("role", "unknown")
        timestamp = msg.get("timestamp", "")

        # Emoji role display
        if role == "user":
            role_display = "👤 User"
        elif role == "assistant":
            model = msg.get("model", "unknown")
            role_display = f"🤖 Assistant/{model}"
        elif role == "error":
            role_display = "❌ Error"
        else:
            role_display = f"❓ {role.capitalize()}"

        # Format timestamp
        if timestamp:
            time_str = timestamp_formatter(timestamp, "%Y-%m-%d %H:%M")
            if time_str == "unknown":
                time_str = timestamp[:16] if len(timestamp) >= 16 else timestamp
        else:
            time_str = "unknown"

        # Content preview
        content = msg.get("content", [])
        content_preview = minify_and_truncate(content, truncate_length)

        header = f"[{hex_id}] {role_display} ({time_str})"
        return f"{header}\n  {content_preview}"

    return format_one_message


# ============================================================================
# Convenience wrappers
# ============================================================================

def format_for_ai_context(messages: list[dict]) -> str:
    """Format messages for AI context (title/summary)."""
    return format_messages(messages, format_message_for_ai_context)


def format_for_safety_check(messages: list[dict]) -> str:
    """Format messages for safety check."""
    return format_messages(messages, format_message_for_safety_check)


def format_for_show(messages: list[dict]) -> str:
    """Format messages for /show."""
    return format_messages(messages, format_message_for_show)
