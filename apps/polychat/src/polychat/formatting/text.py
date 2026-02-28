"""Core text conversion, truncation, and bordered-message utilities."""

from __future__ import annotations

import re
import unicodedata
from typing import Callable, TypeVar

from .constants import BORDERLINE_CHAR, BORDERLINE_WIDTH, TRUNCATE_SEARCH_RADIUS

T = TypeVar("T")


def text_to_lines(text: str) -> list[str]:
    """Convert multiline text to line array with trimming."""
    lines = text.split("\n")

    start = 0
    for index, line in enumerate(lines):
        if line.strip():
            start = index
            break
    else:
        return []

    end = len(lines)
    for index in range(len(lines) - 1, -1, -1):
        if lines[index].strip():
            end = index + 1
            break

    return lines[start:end]


def lines_to_text(lines: list[str]) -> str:
    """Convert line array back to text."""
    return "\n".join(lines)


def minify_text(text: str) -> str:
    """Collapse repeated whitespace to single spaces."""
    return re.sub(r"\s+", " ", text).strip()


def _is_truncate_boundary(character: str) -> bool:
    """Return True when character is a Unicode separator or punctuation."""
    return bool(character) and unicodedata.category(character).startswith(("Z", "P"))


def _find_truncate_position(text: str, target: int, search_radius: int) -> int | None:
    """Find the best position to truncate text near the target."""
    search_start = max(0, target - search_radius)

    for pos in range(target, search_start - 1, -1):
        if pos < len(text) and _is_truncate_boundary(text[pos]):
            while pos > 0 and _is_truncate_boundary(text[pos - 1]):
                pos -= 1
            return pos if pos > 0 else None

    return None


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to max_length, preferring to break at word boundaries."""
    if max_length <= 0:
        return ""

    if len(text) <= max_length:
        return text

    if len(suffix) >= max_length:
        return suffix[:max_length]

    target = max_length - len(suffix)

    break_pos = _find_truncate_position(text, target, TRUNCATE_SEARCH_RADIUS)

    if break_pos is not None:
        truncated = text[:break_pos].rstrip()
    else:
        truncated = text[:target].rstrip()

    if not truncated:
        truncated = text[:target]

    return truncated + suffix


def make_borderline(width: int | None = None, char: str | None = None) -> str:
    """Create a borderline."""
    return (char or BORDERLINE_CHAR) * (width or BORDERLINE_WIDTH)


def format_messages(
    messages: list[T],
    message_formatter: Callable[[T], str],
    borderline_width: int | None = None,
) -> str:
    """Format messages with borderlines using custom formatter."""
    borderline = make_borderline(borderline_width)
    parts = []

    for message in messages:
        parts.append(borderline)
        parts.append(message_formatter(message))

    parts.append(borderline)
    return "\n".join(parts)
