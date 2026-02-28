"""Shared helpers for provider implementations."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from ..formatting.text import lines_to_text

if TYPE_CHECKING:
    from ..domain.chat import ChatMessage


def format_chat_messages(chat_messages: Sequence[ChatMessage]) -> list[dict[str, str]]:
    """Convert ChatMessage objects into simple role/content dicts for provider SDKs."""
    formatted: list[dict[str, str]] = []
    for msg in chat_messages:
        formatted.append(
            {
                "role": msg.role,
                "content": lines_to_text(msg.content),
            }
        )
    return formatted
