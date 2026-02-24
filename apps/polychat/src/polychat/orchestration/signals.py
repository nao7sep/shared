"""Command-signal handling helpers for chat orchestration."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from ..commands.types import CommandSignal
from ..logging import log_event
from ..orchestrator_types import (
    BreakAction,
    ContinueAction,
    OrchestratorAction,
    PrintAction,
)
from ..formatting.text import text_to_lines

if TYPE_CHECKING:
    from ..session_manager import SessionManager


class CommandSignalHandlersMixin:
    """Mixin implementing command-signal flow handlers for orchestrator."""

    manager: SessionManager

    async def _handle_command_signal(
        self,
        signal: CommandSignal,
        *,
        current_chat_path: Optional[str],
        current_chat_data: Optional[dict],
    ) -> OrchestratorAction:
        """Handle typed command-layer control signals."""
        if signal.kind == "exit":
            return BreakAction()

        if signal.kind == "new_chat":
            if not signal.chat_path:
                return PrintAction(message="Error: Invalid command signal (missing new chat path)")
            return await self._handle_new_chat(signal.chat_path, current_chat_path, current_chat_data)

        if signal.kind == "open_chat":
            if not signal.chat_path:
                return PrintAction(message="Error: Invalid command signal (missing open chat path)")
            return await self._handle_open_chat(signal.chat_path, current_chat_path, current_chat_data)

        if signal.kind == "close_chat":
            return await self._handle_close_chat(current_chat_path, current_chat_data)

        if signal.kind == "rename_current":
            if not signal.chat_path:
                return PrintAction(message="Error: Invalid command signal (missing rename path)")
            return self._handle_rename_current(signal.chat_path)

        if signal.kind == "delete_current":
            if signal.value is None:
                return PrintAction(message="Error: Invalid command signal (missing deleted filename)")
            return await self._handle_delete_current(
                signal.value,
                current_chat_path,
                current_chat_data,
            )

        if signal.kind == "apply_retry":
            retry_hex_id = (signal.value or "").strip().lower()
            if not retry_hex_id:
                return PrintAction(message="Retry ID not found")
            return await self._handle_apply_retry(current_chat_path, current_chat_data, retry_hex_id)

        if signal.kind == "cancel_retry":
            return self._handle_cancel_retry()

        if signal.kind == "clear_secret_context":
            return self._handle_clear_secret_context()

        return PrintAction(message=f"Error: Unknown command signal '{signal.kind}'")

    async def _save_chat_if_dirty(
        self,
        chat_path: Optional[str],
        chat_data: Optional[dict],
    ) -> None:
        """Persist chat only when command handlers marked state as dirty."""
        await self.manager.save_current_chat(chat_path=chat_path, chat_data=chat_data)

    async def _handle_new_chat(
        self,
        new_chat_path: str,
        current_chat_path: Optional[str],
        current_chat_data: Optional[dict],
    ) -> OrchestratorAction:
        """Handle create-and-switch to new chat path."""

        if current_chat_path and current_chat_data:
            await self.manager.save_current_chat(
                chat_path=current_chat_path,
                chat_data=current_chat_data,
            )

        # Late-bind through orchestrator module for test patch compatibility.
        from .. import orchestrator as orchestrator_module

        new_chat_data = orchestrator_module.chat.load_chat(new_chat_path)
        self.manager.switch_chat(new_chat_path, new_chat_data)

        await self.manager.save_current_chat(
            chat_path=new_chat_path,
            chat_data=new_chat_data,
        )

        log_event(
            "chat_switch",
            chat_file=new_chat_path,
            trigger="new",
            previous_chat_file=current_chat_path,
            message_count=len(new_chat_data.get("messages", [])),
        )

        return ContinueAction(
            message=f"Created and opened new chat: {new_chat_path}",
            chat_path=new_chat_path,
            chat_data=new_chat_data,
        )

    async def _handle_open_chat(
        self,
        new_chat_path: str,
        current_chat_path: Optional[str],
        current_chat_data: Optional[dict],
    ) -> OrchestratorAction:
        """Handle open-and-switch to selected chat path."""

        if current_chat_path and current_chat_data:
            await self.manager.save_current_chat(
                chat_path=current_chat_path,
                chat_data=current_chat_data,
            )

        # Late-bind through orchestrator module for test patch compatibility.
        from .. import orchestrator as orchestrator_module

        new_chat_data = orchestrator_module.chat.load_chat(new_chat_path)
        self.manager.switch_chat(new_chat_path, new_chat_data)

        log_event(
            "chat_switch",
            chat_file=new_chat_path,
            trigger="open",
            previous_chat_file=current_chat_path,
            message_count=len(new_chat_data.get("messages", [])),
        )

        return ContinueAction(
            message=f"Opened chat: {new_chat_path}",
            chat_path=new_chat_path,
            chat_data=new_chat_data,
        )

    async def _handle_close_chat(
        self,
        current_chat_path: Optional[str],
        current_chat_data: Optional[dict],
    ) -> OrchestratorAction:
        """Handle close-chat signal."""
        if current_chat_path and current_chat_data:
            await self.manager.save_current_chat(
                chat_path=current_chat_path,
                chat_data=current_chat_data,
            )

        self.manager.close_chat()

        log_event(
            "chat_close",
            chat_file=current_chat_path,
            message_count=len(current_chat_data.get("messages", [])) if current_chat_data else 0,
        )

        return ContinueAction(
            message="Chat closed",
            chat_path=None,
            chat_data={},
        )

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
            chat_path=new_chat_path,
        )

    async def _handle_delete_current(
        self,
        deleted_filename: str,
        current_chat_path: Optional[str],
        current_chat_data: Optional[dict],
    ) -> OrchestratorAction:
        """Handle deletion of the currently open chat."""
        self.manager.close_chat()

        log_event(
            "chat_delete",
            chat_file=current_chat_path,
        )

        return ContinueAction(
            message=f"Deleted: {deleted_filename}",
            chat_path=None,
            chat_data={},
        )

    async def _handle_apply_retry(
        self,
        current_chat_path: Optional[str],
        current_chat_data: Optional[dict],
        retry_hex_id: str,
    ) -> OrchestratorAction:
        """Handle apply-retry signal."""
        if not self.manager.retry_mode:
            return PrintAction(message="Not in retry mode")

        if not current_chat_data:
            return PrintAction(message="No chat open")

        retry_attempt = self.manager.get_retry_attempt(retry_hex_id)
        if not retry_attempt:
            return PrintAction(message=f"Retry ID not found: {retry_hex_id}")

        messages = current_chat_data.get("messages", [])
        target_index = self.manager.get_retry_target_index()
        if target_index is None or target_index < 0 or target_index >= len(messages):
            return PrintAction(message="Retry target is no longer valid")

        replace_start = target_index
        if target_index > 0 and messages[target_index - 1].get("role") == "user":
            replace_start = target_index - 1

        existing_user_hex_id = (
            messages[replace_start].get("hex_id")
            if replace_start != target_index
            else None
        )
        existing_assistant_hex_id = messages[target_index].get("hex_id")

        replaced_user_message = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "role": "user",
            "content": text_to_lines(retry_attempt["user_msg"]),
        }
        if isinstance(existing_user_hex_id, str):
            replaced_user_message["hex_id"] = existing_user_hex_id

        replaced_assistant_message = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "role": "assistant",
            "model": self.manager.current_model,
            "content": text_to_lines(retry_attempt["assistant_msg"]),
        }
        citations = retry_attempt.get("citations")
        if citations:
            replaced_assistant_message["citations"] = citations
        if isinstance(existing_assistant_hex_id, str):
            replaced_assistant_message["hex_id"] = existing_assistant_hex_id

        messages[replace_start : target_index + 1] = [
            replaced_user_message,
            replaced_assistant_message,
        ]

        if current_chat_path:
            await self.manager.save_current_chat(
                chat_path=current_chat_path,
                chat_data=current_chat_data,
            )

        self.manager.exit_retry_mode()

        return PrintAction(message=f"Applied retry [{retry_hex_id}]")

    def _handle_cancel_retry(self) -> OrchestratorAction:
        """Handle cancel-retry signal."""
        if not self.manager.retry_mode:
            return PrintAction(message="Not in retry mode")

        self.manager.exit_retry_mode()

        return PrintAction(message="Cancelled retry mode")

    def _handle_clear_secret_context(self) -> OrchestratorAction:
        """Handle clear-secret-context signal."""
        if self.manager.secret_mode:
            self.manager.exit_secret_mode()
            return PrintAction(message="Secret mode disabled")

        return ContinueAction()
