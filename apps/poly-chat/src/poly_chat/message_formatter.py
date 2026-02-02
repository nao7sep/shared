"""Message formatting utilities for PolyChat.

This module handles conversion between multiline text and line arrays,
with proper trimming of leading/trailing whitespace-only lines while
preserving empty lines within content.
"""


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
