"""Chat lifecycle transition handlers for command-signal orchestration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..chat import load_chat
from ..logging import log_event
from .types import ContinueAction, OrchestratorAction

if TYPE_CHECKING:
    from ..session_manager import SessionManager


class ChatSwitchingHandlersMixin:
    """Mixin implementing chat create/open/close/rename/delete transitions."""

    manager: SessionManager

    async def _handle_new_chat(
        self,
        new_chat_path: str,
    ) -> OrchestratorAction:
        """Handle create-and-switch to new chat path."""
        if self.manager.chat_path and self.manager.chat:
            await self.manager.save_current_chat(
                chat_path=self.manager.chat_path,
                chat_data=self.manager.chat,
            )

        previous_path = self.manager.chat_path
        new_chat_data = load_chat(new_chat_path)
        self.manager.switch_chat(new_chat_path, new_chat_data)

        await self.manager.save_current_chat(
            chat_path=new_chat_path,
            chat_data=new_chat_data,
        )

        log_event(
            "chat_switch",
            chat_file=new_chat_path,
            trigger="new",
            previous_chat_file=previous_path,
            message_count=len(new_chat_data.messages),
        )

        return ContinueAction(
            message=f"Created and opened new chat: {new_chat_path}",
        )

    async def _handle_open_chat(
        self,
        new_chat_path: str,
    ) -> OrchestratorAction:
        """Handle open-and-switch to selected chat path."""
        if self.manager.chat_path and self.manager.chat:
            await self.manager.save_current_chat(
                chat_path=self.manager.chat_path,
                chat_data=self.manager.chat,
            )

        previous_path = self.manager.chat_path
        new_chat_data = load_chat(new_chat_path)
        self.manager.switch_chat(new_chat_path, new_chat_data)

        log_event(
            "chat_switch",
            chat_file=new_chat_path,
            trigger="open",
            previous_chat_file=previous_path,
            message_count=len(new_chat_data.messages),
        )

        return ContinueAction(
            message=f"Opened chat: {new_chat_path}",
        )

    async def _handle_close_chat(self) -> OrchestratorAction:
        """Handle close-chat signal."""
        chat_path = self.manager.chat_path
        chat_data = self.manager.chat

        if chat_path and chat_data:
            await self.manager.save_current_chat(
                chat_path=chat_path,
                chat_data=chat_data,
            )

        message_count = len(chat_data.messages) if chat_data else 0
        self.manager.close_chat()

        log_event(
            "chat_close",
            chat_file=chat_path,
            message_count=message_count,
        )

        return ContinueAction(message="Chat closed")

    def _handle_rename_current(self, new_chat_path: str) -> OrchestratorAction:
        """Handle current chat path update after rename."""
        old_chat_path = self.manager.chat_path
        self.manager.chat_path = new_chat_path

        log_event(
            "chat_rename",
            old_chat_file=old_chat_path,
            new_chat_file=new_chat_path,
        )

        return ContinueAction(
            message=f"Renamed to: {new_chat_path}",
        )

    async def _handle_delete_current(
        self,
        deleted_filename: str,
    ) -> OrchestratorAction:
        """Handle deletion of the currently open chat."""
        current_chat_path = self.manager.chat_path
        self.manager.close_chat()

        log_event(
            "chat_delete",
            chat_file=current_chat_path,
        )

        return ContinueAction(message=f"Deleted: {deleted_filename}")
