"""Chat persistence helpers for session state."""

from __future__ import annotations

from typing import Any, Optional

from .state import SessionState


async def save_current_chat(
    state: SessionState,
    *,
    chat_path: Optional[str] = None,
    chat_data: Optional[dict[str, Any]] = None,
) -> bool:
    """Persist current chat state.

    Returns True when a save was performed, False when skipped.
    """
    path = chat_path if chat_path is not None else state.chat_path
    data = chat_data if chat_data is not None else state.chat

    if not path or not isinstance(data, dict):
        return False

    from .. import chat as chat_module

    await chat_module.save_chat(path, data)
    return True

