"""User-message preparation handlers for chat orchestration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from ..session.state import has_pending_error, pending_error_guidance
from .types import (
    ActionMode,
    OrchestratorAction,
    PrintAction,
    SendAction,
)

if TYPE_CHECKING:
    from ..session_manager import SessionManager


class MessageEntryHandlersMixin:
    """Mixin implementing user-message flow and send-action preparation."""

    manager: SessionManager

    def _build_send_action(
        self,
        *,
        messages: list[dict],
        mode: ActionMode,
        search_enabled: Optional[bool] = None,
        retry_user_input: Optional[str] = None,
        assistant_hex_id: Optional[str] = None,
        chat_path: Optional[str] = None,
        chat_data: Optional[dict] = None,
    ) -> OrchestratorAction:
        """Build a send action with optional execution metadata."""
        return SendAction(
            messages=messages,
            mode=mode,
            search_enabled=search_enabled,
            retry_user_input=retry_user_input,
            assistant_hex_id=assistant_hex_id,
            chat_path=chat_path,
            chat_data=chat_data,
        )

    async def handle_user_message(
        self,
        user_input: str,
        chat_path: Optional[str],
        chat_data: Optional[dict],
    ) -> OrchestratorAction:
        """Process user input and return the next orchestration action."""
        if not chat_path:
            return PrintAction(
                message=(
                    "\nNo chat is currently open.\n"
                    "Use /new to create a new chat or /open to open an existing one."
                )
            )

        if not isinstance(chat_data, dict):
            return PrintAction(message="\nNo chat data loaded.")

        if has_pending_error(chat_data) and not self.manager.retry_mode and not self.manager.secret_mode:
            return PrintAction(message=pending_error_guidance())

        if self.manager.secret_mode:
            return await self._handle_secret_message(user_input, chat_data)

        if self.manager.retry_mode:
            return await self._handle_retry_message(user_input, chat_data)

        return await self._handle_normal_message(user_input, chat_data, chat_path)

    async def _handle_secret_message(
        self,
        user_input: str,
        chat_data: dict,
    ) -> OrchestratorAction:
        """Handle one message while secret mode is enabled."""
        from .. import orchestrator as orchestrator_module

        secret_context = orchestrator_module.chat.get_messages_for_ai(chat_data)
        temp_messages = secret_context + [{"role": "user", "content": user_input}]

        return self._build_send_action(
            messages=temp_messages,
            mode="secret",
        )

    async def _handle_retry_message(
        self,
        user_input: str,
        chat_data: dict,
    ) -> OrchestratorAction:
        """Handle one message while retry mode is enabled."""
        from .. import orchestrator as orchestrator_module

        try:
            retry_context = self.manager.get_retry_context()
        except ValueError:
            retry_context = orchestrator_module.chat.get_retry_context_for_last_interaction(chat_data)
            target_index = len(chat_data.get("messages", [])) - 1
            self.manager.enter_retry_mode(
                retry_context,
                target_index=target_index if target_index >= 0 else None,
            )
            retry_context = self.manager.get_retry_context()

        temp_messages = retry_context + [{"role": "user", "content": user_input}]

        return self._build_send_action(
            messages=temp_messages,
            mode="retry",
            retry_user_input=user_input,
            assistant_hex_id=self.manager.reserve_hex_id(),
        )

    async def _handle_normal_message(
        self,
        user_input: str,
        chat_data: dict,
        chat_path: str,
    ) -> OrchestratorAction:
        """Handle one message in normal mode and persist the user turn pre-send."""
        from .. import orchestrator as orchestrator_module

        orchestrator_module.chat.add_user_message(chat_data, user_input)
        new_msg_index = len(chat_data["messages"]) - 1
        self.manager.assign_message_hex_id(new_msg_index)

        messages = orchestrator_module.chat.get_messages_for_ai(chat_data)

        return self._build_send_action(
            messages=messages,
            mode="normal",
            chat_path=chat_path,
            chat_data=chat_data,
        )
