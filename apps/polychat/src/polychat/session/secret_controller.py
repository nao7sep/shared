"""Secret mode state machine.

Encapsulates all secret-mode state and transitions. Instantiated by
SessionManager and exposed as ``manager.secret``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from ..ai.types import Citation
from ..domain.chat import ChatMessage


@dataclass
class SecretController:
    """Owns the secret mode lifecycle: enter → converse → exit."""

    _conflict_check: Callable[[], bool] = field(default=lambda: False, repr=False)

    active: bool = False
    base_messages: list[ChatMessage] = field(default_factory=list)
    secret_messages: list[ChatMessage] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Transitions
    # ------------------------------------------------------------------

    def enter(self, base_messages: list[ChatMessage]) -> None:
        """Enter secret mode and store a context snapshot."""
        if self._conflict_check():
            raise ValueError("Cannot enter secret mode while in retry mode")

        self.active = True
        self.base_messages = base_messages.copy()
        self.secret_messages.clear()

    def exit(self) -> None:
        """Exit secret mode and clear secret state."""
        self.active = False
        self.base_messages.clear()
        self.secret_messages.clear()

    def clear(self) -> None:
        """Unconditional reset (used by clear_chat_scoped_state)."""
        self.exit()

    # ------------------------------------------------------------------
    # Context
    # ------------------------------------------------------------------

    def get_context(self) -> list[ChatMessage]:
        """Return the current secret conversation context.

        Raises:
            ValueError: If not in secret mode.
        """
        if not self.active:
            raise ValueError("Not in secret mode")
        return self.base_messages + self.secret_messages

    def has_pending_error(self) -> bool:
        """Return True when the secret transcript ends in an error."""
        return bool(self.secret_messages and self.secret_messages[-1].role == "error")

    def append_success(
        self,
        user_msg: str,
        assistant_msg: str,
        *,
        model: str,
        citations: list[Citation] | None = None,
    ) -> None:
        """Append one successful secret turn to the runtime-only transcript."""
        if not self.active:
            raise ValueError("Not in secret mode")

        self.secret_messages.append(ChatMessage.new_user(user_msg))
        self.secret_messages.append(
            ChatMessage.new_assistant(
                assistant_msg,
                model=model,
                citations=citations,
            )
        )

    def append_error(
        self,
        error_msg: str,
        *,
        user_msg: str | None = None,
        details: dict[str, object] | None = None,
    ) -> None:
        """Append a secret-only error interaction to the runtime transcript."""
        if not self.active:
            raise ValueError("Not in secret mode")

        if user_msg is not None:
            self.secret_messages.append(ChatMessage.new_user(user_msg))
        self.secret_messages.append(ChatMessage.new_error(error_msg, details=details))
