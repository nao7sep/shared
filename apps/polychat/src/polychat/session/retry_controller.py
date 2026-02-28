"""Retry mode state machine.

Encapsulates all retry-related state and transitions. Instantiated by
SessionManager and exposed as ``manager.retry``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .. import hex_id as hex_id_mod
from ..ai.types import Citation
from ..domain.chat import ChatMessage, RetryAttempt


@dataclass
class RetryController:
    """Owns the retry mode lifecycle: enter → attempt(s) → apply/cancel → exit."""

    _hex_id_set: set[str]
    _conflict_check: Callable[[], bool] = field(default=lambda: False, repr=False)

    active: bool = False
    base_messages: list[ChatMessage] = field(default_factory=list)
    target_index: int | None = None
    attempts: dict[str, RetryAttempt] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Transitions
    # ------------------------------------------------------------------

    def enter(
        self,
        base_messages: list[ChatMessage],
        target_index: int | None = None,
    ) -> None:
        """Enter retry mode with a frozen message context."""
        if self._conflict_check():
            raise ValueError("Cannot enter retry mode while in secret mode")

        self.active = True
        self.base_messages = base_messages.copy()
        self.target_index = target_index
        self._discard_attempt_hex_ids()
        self.attempts.clear()

    def exit(self) -> None:
        """Exit retry mode and discard all retry state."""
        self.active = False
        self.base_messages.clear()
        self.target_index = None
        self._discard_attempt_hex_ids()
        self.attempts.clear()

    def clear(self) -> None:
        """Unconditional reset (used by clear_chat_scoped_state)."""
        self.exit()

    # ------------------------------------------------------------------
    # Context
    # ------------------------------------------------------------------

    def get_context(self) -> list[ChatMessage]:
        """Return the frozen retry context.

        Raises:
            ValueError: If not in retry mode.
        """
        if not self.active:
            raise ValueError("Not in retry mode")
        return self.base_messages

    # ------------------------------------------------------------------
    # Attempts
    # ------------------------------------------------------------------

    def add_attempt(
        self,
        user_msg: str,
        assistant_msg: str,
        retry_hex_id: str | None = None,
        citations: list[Citation] | None = None,
    ) -> str:
        """Store a retry attempt and return its runtime hex ID."""
        if not self.active:
            raise ValueError("Not in retry mode")

        if retry_hex_id is None:
            retry_hex_id = hex_id_mod.generate_hex_id(self._hex_id_set)
        else:
            self._hex_id_set.add(retry_hex_id)

        self.attempts[retry_hex_id] = RetryAttempt(
            user_msg=user_msg,
            assistant_msg=assistant_msg,
            citations=citations if citations else None,
        )
        return retry_hex_id

    def get_attempt(self, retry_hex_id: str) -> RetryAttempt | None:
        """Get one retry attempt by runtime hex ID."""
        return self.attempts.get(retry_hex_id)

    def latest_attempt_id(self) -> str | None:
        """Return the most recently generated retry attempt hex ID."""
        if not self.attempts:
            return None
        return next(reversed(self.attempts))

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _discard_attempt_hex_ids(self) -> None:
        for hid in list(self.attempts.keys()):
            self._hex_id_set.discard(hid)
