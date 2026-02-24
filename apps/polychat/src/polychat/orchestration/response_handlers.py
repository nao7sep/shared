"""AI response/error/cancel handlers for chat orchestration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, cast

from ..logging import sanitize_error_message
from ..orchestrator_types import ActionMode, ContinueAction, OrchestratorAction, PrintAction
from ..ai.types import Citation

if TYPE_CHECKING:
    from ..session_manager import SessionManager


class ResponseHandlersMixin:
    """Mixin implementing post-send success/error/cancel chat mutations."""

    manager: SessionManager

    async def handle_ai_response(
        self,
        response_text: str,
        chat_path: str | None,
        chat_data: dict[str, Any] | None,
        mode: ActionMode,
        user_input: Optional[str] = None,
        assistant_hex_id: Optional[str] = None,
        citations: Optional[list[Citation]] = None,
    ) -> OrchestratorAction:
        """Handle successful AI response for the given mode."""
        from .. import orchestrator as orchestrator_module

        if mode == "retry":
            citations_payload = cast(Optional[list[dict[str, Any]]], citations)
            if user_input and assistant_hex_id:
                self.manager.add_retry_attempt(
                    user_input,
                    response_text,
                    retry_hex_id=assistant_hex_id,
                    citations=citations_payload,
                )
            return ContinueAction()

        if mode == "secret":
            if assistant_hex_id:
                self.manager.release_hex_id(assistant_hex_id)
            return ContinueAction()

        if mode == "normal":
            if not chat_path or not isinstance(chat_data, dict):
                return PrintAction(message="\nError: chat context missing for normal-mode response.")
            orchestrator_module.chat.add_assistant_message(
                chat_data,
                response_text,
                self.manager.current_model,
                citations=cast(Optional[list[dict[str, Any]]], citations),
            )
            if chat_data.get("messages"):
                if assistant_hex_id:
                    chat_data["messages"][-1]["hex_id"] = assistant_hex_id
                else:
                    new_msg_index = len(chat_data["messages"]) - 1
                    self.manager.assign_message_hex_id(new_msg_index)
            await self.manager.save_current_chat(
                chat_path=chat_path,
                chat_data=chat_data,
            )
            return ContinueAction()

        return ContinueAction()

    async def rollback_pre_send_failure(
        self,
        *,
        chat_path: Optional[str],
        chat_data: Optional[dict],
        mode: ActionMode,
        assistant_hex_id: Optional[str] = None,
    ) -> bool:
        """Rollback pre-send normal-mode state when provider validation fails."""
        if assistant_hex_id:
            self.manager.release_hex_id(assistant_hex_id)

        if mode != "normal" or not chat_path or not isinstance(chat_data, dict):
            return False

        messages = chat_data.get("messages")
        if not isinstance(messages, list) or not messages:
            return False
        if messages[-1].get("role") != "user":
            return False

        self.manager.pop_message(-1, chat_data)
        await self.manager.save_current_chat(
            chat_path=chat_path,
            chat_data=chat_data,
        )
        return True

    async def handle_ai_error(
        self,
        error: Exception,
        chat_path: str | None,
        chat_data: dict[str, Any] | None,
        mode: ActionMode,
        assistant_hex_id: Optional[str] = None,
    ) -> PrintAction:
        """Handle AI error and return a user-facing action."""
        from .. import orchestrator as orchestrator_module

        if mode == "normal":
            if not chat_path or not isinstance(chat_data, dict):
                return PrintAction(message=f"\nError: {error}")
            if assistant_hex_id:
                self.manager.release_hex_id(assistant_hex_id)
            if chat_data["messages"] and chat_data["messages"][-1]["role"] == "user":
                self.manager.pop_message(-1, chat_data)

            sanitized_error = sanitize_error_message(str(error))
            orchestrator_module.chat.add_error_message(
                chat_data,
                sanitized_error,
                {"provider": self.manager.current_ai, "model": self.manager.current_model},
            )
            new_msg_index = len(chat_data["messages"]) - 1
            self.manager.assign_message_hex_id(new_msg_index)
            await self.manager.save_current_chat(
                chat_path=chat_path,
                chat_data=chat_data,
            )
        elif assistant_hex_id:
            self.manager.release_hex_id(assistant_hex_id)

        return PrintAction(message=f"\nError: {error}")

    async def handle_user_cancel(
        self,
        chat_data: dict[str, Any] | None,
        mode: ActionMode,
        chat_path: Optional[str] = None,
        assistant_hex_id: Optional[str] = None,
    ) -> PrintAction:
        """Handle user cancellation during streamed AI response."""
        if mode == "normal":
            if not chat_path or not isinstance(chat_data, dict):
                return PrintAction(message="\n[Message cancelled]")
            if assistant_hex_id:
                self.manager.release_hex_id(assistant_hex_id)
            if chat_data["messages"] and chat_data["messages"][-1]["role"] == "user":
                self.manager.pop_message(-1, chat_data)
            await self.manager.save_current_chat(
                chat_path=chat_path,
                chat_data=chat_data,
            )

        if mode in ("retry", "secret") and assistant_hex_id:
            self.manager.release_hex_id(assistant_hex_id)

        return PrintAction(message="\n[Message cancelled]")
