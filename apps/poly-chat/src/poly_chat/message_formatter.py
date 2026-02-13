"""Message formatting utilities for PolyChat.

This module handles conversion between multiline text and line arrays,
with proper trimming of leading/trailing whitespace-only lines while
preserving empty lines within content.
"""

import re


def text_to_lines(text: str) -> list[str]:
    """Convert multiline text to line array with trimming.

    Args:
        text: Input text (may have leading/trailing whitespace-only lines)

    Returns:
        List of lines with leading/trailing whitespace-only lines removed

    Algorithm:
    1. Split by \\n
    2. Find first non-whitespace-only line
    3. Find last non-whitespace-only line
    4. Return lines in that range
    5. Preserve empty lines within content as ""

    Example:
        Input: "\\n\\nFirst line\\n\\nSecond line\\n\\n"
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
        Joined text with \\n
    """
    return "\n".join(lines)


def format_messages_for_context(
    messages: list[dict],
    separator_width: int = 60,
    include_role: bool = True,
    include_hex_id: bool = False,
    uppercase_role: bool = False,
) -> str:
    """Format messages with separator lines for AI context.

    Args:
        messages: List of message dictionaries
        separator_width: Width of separator line (default 60)
        include_role: Include role prefix on first line of each message
        include_hex_id: Include [hex_id] before role (for safety checks)
        uppercase_role: Use UPPERCASE for role names

    Returns:
        Formatted string with separator-delimited messages

    Format:
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        user: first line of message
        continuation line
        last line
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        assistant: first line
        ...
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """
    separator = "━" * separator_width
    formatted_parts = []

    for msg in messages:
        # Add separator before each message
        formatted_parts.append(separator)

        # Get message components
        role = msg.get("role", "unknown")
        if uppercase_role:
            role = role.upper()

        content_parts = msg.get("content", [])
        if isinstance(content_parts, list):
            content = lines_to_text(content_parts)
        else:
            content = str(content_parts)

        # Build message line(s)
        if include_role:
            if include_hex_id:
                hex_id = msg.get("hex_id", "")
                hex_prefix = f"[{hex_id}] " if hex_id else ""
                first_line = f"{hex_prefix}{role}: {content}"
            else:
                first_line = f"{role}: {content}"
            formatted_parts.append(first_line)
        else:
            formatted_parts.append(content)

    # Add final separator after all messages
    formatted_parts.append(separator)

    return "\n".join(formatted_parts)


def format_message_content_only(
    content: str | list[str],
    separator_width: int = 60,
) -> str:
    """Format single message content with separators (for /show command).

    Args:
        content: Message content as string or list of lines
        separator_width: Width of separator line (default 60)

    Returns:
        Formatted string with separator-delimited content

    Format:
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        message content line 1
        message content line 2
        ...
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """
    separator = "━" * separator_width

    if isinstance(content, list):
        content_text = lines_to_text(content)
    else:
        content_text = str(content)

    return f"{separator}\n{content_text}\n{separator}"


def minify_and_truncate(
    content: str | list[str],
    max_length: int,
) -> str:
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
