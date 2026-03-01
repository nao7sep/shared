"""AI response/error/cancel handlers for chat orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from ..chat import add_assistant_message, add_error_message
from ..domain.chat import ChatDocument
from ..logging import sanitize_error_message
from .types import ActionMode, ContinueAction, OrchestratorAction, PrintAction
from ..ai.types import Citation

if TYPE_CHECKING:
    from ..session_manager import SessionManager


@dataclass(slots=True, frozen=True)
class ResponseTransitionState:
    """Derived transition state used by response-mode handlers."""

    mode: ActionMode
    has_chat_context: bool
    has_assistant_hex_id: bool


def build_transition_state(
    mode: ActionMode,
    *,
    chat_path: str | None,
    chat_data: ChatDocument | None,
    assistant_hex_id: str | None,
) -> ResponseTransitionState:
    """Build derived state for response-mode transition decisions."""
    has_chat_context = bool(chat_path) and chat_data is not None
    has_assistant_hex_id = bool(assistant_hex_id)
    return ResponseTransitionState(
        mode=mode,
        has_chat_context=has_chat_context,
        has_assistant_hex_id=has_assistant_hex_id,
    )


def can_mutate_normal_chat(state: ResponseTransitionState) -> bool:
    """Return True when normal-mode chat mutations are valid."""
    return state.mode == "normal" and state.has_chat_context


def has_trailing_user_message(chat_data: ChatDocument | None) -> bool:
    """Return True when chat_data ends with a user message."""
    if chat_data is None:
        return False
    messages = chat_data.messages
    if not messages:
        return False
    return messages[-1].role == "user"


def should_release_for_rollback(state: ResponseTransitionState) -> bool:
    """Rollback always releases reserved hex IDs when one exists."""
    return state.has_assistant_hex_id


def should_release_for_error(state: ResponseTransitionState) -> bool:
    """Return True when error handling should release reserved hex IDs."""
    if state.mode == "normal":
        return state.has_chat_context and state.has_assistant_hex_id
    return state.has_assistant_hex_id


def should_release_for_cancel(state: ResponseTransitionState) -> bool:
    """Return True when cancel handling should release reserved hex IDs."""
    if state.mode == "normal":
        return state.has_chat_context and state.has_assistant_hex_id
    return state.has_assistant_hex_id


def should_rollback_pre_send(
    state: ResponseTransitionState,
    chat_data: ChatDocument | None,
) -> bool:
    """Return True when pre-send rollback should mutate persisted chat state."""
    return can_mutate_normal_chat(state) and has_trailing_user_message(chat_data)


def build_provider_error_details(manager: SessionManager) -> dict[str, str]:
    """Build the standard provider/model error payload."""
    return {
        "provider": manager.current_ai,
        "model": manager.current_model,
    }


class ResponseHandlersMixin:
    """Mixin implementing post-send success/error/cancel chat mutations."""

    manager: SessionManager

    async def handle_ai_response(
        self,
        response_text: str,
        chat_path: str | None,
        chat_data: ChatDocument | None,
        mode: ActionMode,
        user_input: Optional[str] = None,
        assistant_hex_id: Optional[str] = None,
        citations: Optional[list[Citation]] = None,
    ) -> OrchestratorAction:
        """Handle successful AI response for the given mode."""
        if mode == "retry":
            if user_input and assistant_hex_id:
                self.manager.retry.add_attempt(
                    user_input,
                    response_text,
                    retry_hex_id=assistant_hex_id,
                    citations=citations,
                )
            return ContinueAction()

        if mode == "secret":
            if user_input:
                self.manager.secret.append_success(
                    user_input,
                    response_text,
                    model=self.manager.current_model,
                    citations=citations,
                )
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
                return PrintAction(message="Error: chat context missing for normal-mode response.")
            assert chat_path is not None
            assert chat_data is not None
            add_assistant_message(
                chat_data,
                response_text,
                self.manager.current_model,
                citations=citations,
            )
            if chat_data.messages:
                if assistant_hex_id:
                    chat_data.messages[-1].hex_id = assistant_hex_id
                else:
                    new_msg_index = len(chat_data.messages) - 1
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
        chat_data: Optional[ChatDocument],
        mode: ActionMode,
        error_message: str,
        assistant_hex_id: Optional[str] = None,
    ) -> bool:
        """Handle failures that happen before the provider request starts."""
        transition = build_transition_state(
            mode,
            chat_path=chat_path,
            chat_data=chat_data,
            assistant_hex_id=assistant_hex_id,
        )
        sanitized_error = sanitize_error_message(error_message)

        if assistant_hex_id and should_release_for_rollback(transition):
            self.manager.release_hex_id(assistant_hex_id)

        if mode == "secret":
            self.manager.secret.append_error(
                sanitized_error,
                details=build_provider_error_details(self.manager),
            )
            return False

        if not should_rollback_pre_send(transition, chat_data):
            return False

        assert chat_path is not None
        assert chat_data is not None
        if chat_data is not self.manager.chat:
            return False

        self.manager.pop_message(-1, chat_data)
        add_error_message(
            chat_data,
            sanitized_error,
            build_provider_error_details(self.manager),
        )
        new_msg_index = len(chat_data.messages) - 1
        self.manager.assign_message_hex_id(new_msg_index)
        await self.manager.save_current_chat(
            chat_path=chat_path,
            chat_data=chat_data,
        )
        return True

    async def handle_ai_error(
        self,
        error: Exception,
        chat_path: str | None,
        chat_data: ChatDocument | None,
        mode: ActionMode,
        user_input: Optional[str] = None,
        assistant_hex_id: Optional[str] = None,
    ) -> PrintAction:
        """Handle AI error and return a user-facing action."""
        transition = build_transition_state(
            mode,
            chat_path=chat_path,
            chat_data=chat_data,
            assistant_hex_id=assistant_hex_id,
        )
        sanitized_error = sanitize_error_message(str(error))

        if mode == "normal":
            if not can_mutate_normal_chat(transition):
                return PrintAction(message=f"Error: {sanitized_error}")
            assert chat_path is not None
            assert chat_data is not None
            if assistant_hex_id and should_release_for_error(transition):
                self.manager.release_hex_id(assistant_hex_id)
            if chat_data is not self.manager.chat:
                return PrintAction(message=f"Error: {sanitized_error}")

            add_error_message(
                chat_data,
                sanitized_error,
                build_provider_error_details(self.manager),
            )
            new_msg_index = len(chat_data.messages) - 1
            self.manager.assign_message_hex_id(new_msg_index)
            await self.manager.save_current_chat(
                chat_path=chat_path,
                chat_data=chat_data,
            )
        elif mode == "secret":
            self.manager.secret.append_error(
                sanitized_error,
                user_msg=user_input,
                details=build_provider_error_details(self.manager),
            )
            if assistant_hex_id and should_release_for_error(transition):
                self.manager.release_hex_id(assistant_hex_id)
        elif assistant_hex_id and should_release_for_error(transition):
            self.manager.release_hex_id(assistant_hex_id)

        return PrintAction(message=f"Error: {sanitized_error}")

    async def handle_user_cancel(
        self,
        chat_data: ChatDocument | None,
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
                return PrintAction(message="[Message cancelled]")
            assert chat_path is not None
            assert chat_data is not None
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

        return PrintAction(message="[Message cancelled]")
