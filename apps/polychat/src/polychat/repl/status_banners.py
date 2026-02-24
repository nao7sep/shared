"""Status and startup banner rendering for REPL."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..constants import (
    BORDERLINE_CHAR,
    BORDERLINE_WIDTH,
    EMOJI_MODE_RETRY,
    EMOJI_MODE_SECRET,
)
from ..session.state import has_pending_error, pending_error_guidance
from ..session_manager import SessionManager


def print_startup_banner(
    manager: SessionManager,
    profile_data: dict,
    chat_path: Optional[str],
) -> None:
    """Print REPL startup context and key usage hints."""
    configured_ais = []
    for provider, model in profile_data["models"].items():
        if provider in profile_data.get("api_keys", {}):
            configured_ais.append(f"{provider} ({model})")

    borderline = BORDERLINE_CHAR * BORDERLINE_WIDTH

    print(borderline)
    print("PolyChat - Multi-AI CLI Chat Tool")
    print(borderline)
    print(f"Current Provider: {manager.current_ai}")
    print(f"Current Model:    {manager.current_model}")
    print(f"Configured AIs:   {', '.join(configured_ais)}")
    if chat_path:
        print(f"Chat:             {Path(chat_path).name}")
    else:
        print("Chat:             None (use /new or /open)")
    print()
    if manager.input_mode == "quick":
        print("Input Mode:       quick (Enter sends | Option/Alt+Enter inserts new line)")
    else:
        print("Input Mode:       compose (Enter inserts new line | Option/Alt+Enter sends)")
    print("Ctrl+J also sends in both modes")
    print("Type /help for commands • Ctrl+D to exit")
    print(borderline)
    print()


def print_mode_banner(manager: SessionManager, chat_data: Optional[dict]) -> None:
    """Print mode-state banner shown before each prompt."""
    if has_pending_error(chat_data) and not manager.retry_mode:
        print(pending_error_guidance(compact=True))
    elif manager.retry_mode:
        print(f"{EMOJI_MODE_RETRY} RETRY MODE - Use /apply to accept, /cancel to abort")
    elif manager.secret_mode:
        print(f"{EMOJI_MODE_SECRET} SECRET MODE - Messages not saved to history")
