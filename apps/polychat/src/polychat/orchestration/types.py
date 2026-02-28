"""Typed action models exchanged between orchestrator and REPL."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

from ..domain.chat import ChatDocument, ChatMessage


ActionMode = Literal["normal", "retry", "secret"]


@dataclass(slots=True, frozen=True)
class BreakAction:
    """Stop the REPL loop."""

    kind: Literal["break"] = "break"


@dataclass(slots=True, frozen=True)
class PrintAction:
    """Print a user-facing message in REPL and continue."""

    message: str
    kind: Literal["print"] = "print"


@dataclass(slots=True, frozen=True)
class ContinueAction:
    """Continue REPL loop, optionally updating active chat context."""

    message: str | None = None
    chat_path: str | None = None
    chat_data: ChatDocument | None = None
    kind: Literal["continue"] = "continue"


@dataclass(slots=True, frozen=True)
class SendAction:
    """Dispatch prepared messages to provider execution path."""

    mode: ActionMode
    messages: list[ChatMessage]
    search_enabled: bool | None = None
    retry_user_input: str | None = None
    assistant_hex_id: str | None = None
    chat_path: str | None = None
    chat_data: ChatDocument | None = None
    kind: Literal["send"] = "send"


OrchestratorAction: TypeAlias = BreakAction | PrintAction | ContinueAction | SendAction
