"""Chat orchestration facade for lifecycle, modes, and command signals."""

from __future__ import annotations

from typing import Optional

from . import chat  # noqa: F401 - kept for compatibility with existing patch targets
from .commands.types import CommandResult, CommandSignal
from .orchestration.message_entry import MessageEntryHandlersMixin
from .orchestration.response_handlers import ResponseHandlersMixin
from .orchestration.signals import CommandSignalHandlersMixin
from .orchestration.types import ContinueAction, OrchestratorAction, PrintAction
from .session_manager import SessionManager


class ChatOrchestrator(
    CommandSignalHandlersMixin,
    MessageEntryHandlersMixin,
    ResponseHandlersMixin,
):
    """Thin composer for command-signal, message-entry, and response handlers."""

    def __init__(self, session_manager: SessionManager):
        self.manager = session_manager

    async def handle_command_response(
        self,
        response: CommandResult,
        current_chat_path: Optional[str],
        current_chat_data: Optional[dict],
    ) -> OrchestratorAction:
        """Process command result and return a typed action for REPL."""
        if isinstance(response, CommandSignal):
            return await self._handle_command_signal(
                response,
                current_chat_path=current_chat_path,
                current_chat_data=current_chat_data,
            )

        if isinstance(response, str):
            await self._persist_chat_after_command(current_chat_path, current_chat_data)
            return PrintAction(message=response)

        return ContinueAction()
