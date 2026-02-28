"""Secret mode state machine.

Encapsulates all secret-mode state and transitions. Instantiated by
SessionManager and exposed as ``manager.secret``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from ..domain.chat import ChatMessage


@dataclass
class SecretController:
    """Owns the secret mode lifecycle: enter → converse → exit."""

    _conflict_check: Callable[[], bool] = field(default=lambda: False, repr=False)

    active: bool = False
    base_messages: list[ChatMessage] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Transitions
    # ------------------------------------------------------------------

    def enter(self, base_messages: list[ChatMessage]) -> None:
        """Enter secret mode and store a context snapshot."""
        if self._conflict_check():
            raise ValueError("Cannot enter secret mode while in retry mode")

        self.active = True
        self.base_messages = base_messages.copy()

    def exit(self) -> None:
        """Exit secret mode and clear secret state."""
        self.active = False
        self.base_messages.clear()

    def clear(self) -> None:
        """Unconditional reset (used by clear_chat_scoped_state)."""
        self.exit()

    # ------------------------------------------------------------------
    # Context
    # ------------------------------------------------------------------

    def get_context(self) -> list[ChatMessage]:
        """Return the secret-mode context snapshot.

        Raises:
            ValueError: If not in secret mode.
        """
        if not self.active:
            raise ValueError("Not in secret mode")
        return self.base_messages
