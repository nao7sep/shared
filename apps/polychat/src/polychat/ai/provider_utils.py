"""Shared helpers for provider implementations."""

from __future__ import annotations

from ..formatting.text import lines_to_text


def format_chat_messages(chat_messages: list[dict]) -> list[dict]:
    """Convert PolyChat messages into simple role/content payloads."""
    formatted: list[dict] = []
    for msg in chat_messages:
        formatted.append(
            {
                "role": msg["role"],
                "content": lines_to_text(msg["content"]),
            }
        )
    return formatted
