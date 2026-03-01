"""User-message preparation handlers for chat orchestration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from ..chat import (
    add_user_message,
    filter_messages_for_ai,
    get_messages_for_ai,
)
from ..domain.chat import ChatMessage
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
        messages: list[ChatMessage],
        mode: ActionMode,
        search_enabled: Optional[bool] = None,
        user_input: Optional[str] = None,
        assistant_hex_id: Optional[str] = None,
    ) -> OrchestratorAction:
        """Build a send action with optional execution metadata."""
        return SendAction(
            messages=messages,
            mode=mode,
            search_enabled=search_enabled,
            user_input=user_input,
            assistant_hex_id=assistant_hex_id,
        )

    async def handle_user_message(
        self,
        user_input: str,
    ) -> OrchestratorAction:
        """Process user input and return the next orchestration action."""
        chat_path = self.manager.chat_path
        chat_data = self.manager.chat

        if not chat_path:
            return PrintAction(
                message=(
                    "No chat is currently open.\n"
                    "Use /new to create a new chat or /open to open an existing one."
                )
            )

        if chat_data is None:
            return PrintAction(message="No chat data loaded.")

        if has_pending_error(chat_data) and not self.manager.retry.active and not self.manager.secret.active:
            return PrintAction(message=pending_error_guidance())

        if self.manager.secret.active:
            return await self._handle_secret_message(user_input)

        if self.manager.retry.active:
            return await self._handle_retry_message(user_input)

        return await self._handle_normal_message(user_input)

    async def _handle_secret_message(
        self,
        user_input: str,
    ) -> OrchestratorAction:
        """Handle one message while secret mode is enabled."""
        if self.manager.secret.has_pending_error():
            return PrintAction(
                message=(
                    "Secret mode cannot continue: last secret interaction failed.\n"
                    "Use /secret off to discard the secret branch."
                )
            )

        secret_context = filter_messages_for_ai(self.manager.secret.get_context())
        temp_messages = secret_context + [ChatMessage.new_user(user_input)]

        return self._build_send_action(
            messages=temp_messages,
            mode="secret",
            user_input=user_input,
        )

    async def _handle_retry_message(
        self,
        user_input: str,
    ) -> OrchestratorAction:
        """Handle one message while retry mode is enabled."""
        try:
            retry_context = self.manager.retry.get_context()
        except ValueError:
            self.manager.retry.clear()
            return PrintAction(
                message=(
                    "Retry mode state was inconsistent and has been cleared.\n"
                    "Run /retry again to start a new retry attempt."
                )
            )

        temp_messages = retry_context + [ChatMessage.new_user(user_input)]

        return self._build_send_action(
            messages=temp_messages,
            mode="retry",
            user_input=user_input,
            assistant_hex_id=self.manager.reserve_hex_id(),
        )

    async def _handle_normal_message(
        self,
        user_input: str,
    ) -> OrchestratorAction:
        """Handle one message in normal mode and persist the user turn pre-send."""
        chat_data = self.manager.chat
        add_user_message(chat_data, user_input)
        new_msg_index = len(chat_data.messages) - 1
        self.manager.assign_message_hex_id(new_msg_index)

        messages = get_messages_for_ai(chat_data)

        return self._build_send_action(
            messages=messages,
            mode="normal",
        )
