"""AI response/error/cancel handlers for chat orchestration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, cast

from ..logging import sanitize_error_message
from ..orchestrator_types import ActionMode, ContinueAction, OrchestratorAction, PrintAction
from ..ai.types import Citation
from .response_transitions import (
    build_transition_state,
    can_mutate_normal_chat,
    has_trailing_user_message,
    should_release_for_cancel,
    should_release_for_error,
    should_release_for_rollback,
    should_rollback_pre_send,
)

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
            transition = build_transition_state(
                mode,
                chat_path=chat_path,
                chat_data=chat_data,
                assistant_hex_id=assistant_hex_id,
            )
            if not can_mutate_normal_chat(transition):
                return PrintAction(message="\nError: chat context missing for normal-mode response.")
            assert chat_path is not None
            assert isinstance(chat_data, dict)
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
        transition = build_transition_state(
            mode,
            chat_path=chat_path,
            chat_data=cast(Optional[dict[str, Any]], chat_data),
            assistant_hex_id=assistant_hex_id,
        )

        if assistant_hex_id and should_release_for_rollback(transition):
            self.manager.release_hex_id(assistant_hex_id)

        if not should_rollback_pre_send(
            transition,
            cast(Optional[dict[str, Any]], chat_data),
        ):
            return False

        assert chat_path is not None
        assert isinstance(chat_data, dict)

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

        transition = build_transition_state(
            mode,
            chat_path=chat_path,
            chat_data=chat_data,
            assistant_hex_id=assistant_hex_id,
        )

        if mode == "normal":
            if not can_mutate_normal_chat(transition):
                return PrintAction(message=f"\nError: {error}")
            assert chat_path is not None
            assert isinstance(chat_data, dict)
            if assistant_hex_id and should_release_for_error(transition):
                self.manager.release_hex_id(assistant_hex_id)
            if has_trailing_user_message(chat_data):
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
        elif assistant_hex_id and should_release_for_error(transition):
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
        transition = build_transition_state(
            mode,
            chat_path=chat_path,
            chat_data=chat_data,
            assistant_hex_id=assistant_hex_id,
        )

        if mode == "normal":
            if not can_mutate_normal_chat(transition):
                return PrintAction(message="\n[Message cancelled]")
            assert chat_path is not None
            assert isinstance(chat_data, dict)
            if assistant_hex_id and should_release_for_cancel(transition):
                self.manager.release_hex_id(assistant_hex_id)
            if has_trailing_user_message(chat_data):
                self.manager.pop_message(-1, chat_data)
            await self.manager.save_current_chat(
                chat_path=chat_path,
                chat_data=chat_data,
            )

        if mode in ("retry", "secret") and assistant_hex_id and should_release_for_cancel(transition):
            self.manager.release_hex_id(assistant_hex_id)

        return PrintAction(message="\n[Message cancelled]")
