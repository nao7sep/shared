"""Typed command results exchanged between command layer and orchestrator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias


CommandSignalKind = Literal[
    "exit",
    "new_chat",
    "open_chat",
    "close_chat",
    "rename_current",
    "delete_current",
    "apply_retry",
    "cancel_retry",
    "clear_secret_context",
]


@dataclass(slots=True, frozen=True)
class CommandSignal:
    """Structured control-flow signal emitted by command handlers."""

    kind: CommandSignalKind
    chat_path: str | None = None
    value: str | None = None


CommandResult: TypeAlias = str | CommandSignal | None
