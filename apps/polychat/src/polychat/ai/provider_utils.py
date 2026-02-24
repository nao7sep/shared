"""Shared helpers for provider implementations."""

from __future__ import annotations

from collections.abc import Sequence

from ..formatting.text import lines_to_text


def format_chat_messages(chat_messages: Sequence[dict[str, object]]) -> list[dict[str, str]]:
    """Convert PolyChat messages into simple role/content payloads."""
    formatted: list[dict[str, str]] = []
    for msg in chat_messages:
        role = str(msg.get("role", ""))
        raw_content = msg.get("content", "")
        if isinstance(raw_content, list):
            content = lines_to_text([str(part) for part in raw_content])
        else:
            content = str(raw_content)
        formatted.append(
            {
                "role": role,
                "content": content,
            }
        )
    return formatted
