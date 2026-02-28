"""Typed action models exchanged between orchestrator and REPL."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

from ..domain.chat import ChatMessage


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
    """Continue REPL loop, optionally printing a message.

    Chat state is always read from SessionManager — this action
    does not carry chat_path or chat_data.
    """

    message: str | None = None
    kind: Literal["continue"] = "continue"


@dataclass(slots=True, frozen=True)
class SendAction:
    """Dispatch prepared messages to provider execution path."""

    mode: ActionMode
    messages: list[ChatMessage]
    search_enabled: bool | None = None
    retry_user_input: str | None = None
    assistant_hex_id: str | None = None
    kind: Literal["send"] = "send"


OrchestratorAction: TypeAlias = BreakAction | PrintAction | ContinueAction | SendAction
