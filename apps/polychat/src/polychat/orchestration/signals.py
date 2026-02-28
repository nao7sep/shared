"""Command-signal handling helpers for chat orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Awaitable, Callable, Optional

from ..commands.types import CommandSignal
from ..domain.chat import ChatDocument, ChatMessage, RetryAttempt
from ..formatting.text import text_to_lines
from .types import (
    BreakAction,
    ContinueAction,
    OrchestratorAction,
    PrintAction,
)
from .chat_switching import ChatSwitchingHandlersMixin

if TYPE_CHECKING:
    from ..session_manager import SessionManager

SignalDispatchHandler = Callable[
    [CommandSignal, Optional[str], Optional[ChatDocument]],
    Awaitable[OrchestratorAction],
]

TimestampFactory = Callable[[], str]


@dataclass(slots=True, frozen=True)
class RetryReplacementPlan:
    """Planned slice replacement for applying one retry attempt."""

    replace_start: int
    replace_end: int
    replacement_messages: list[ChatMessage]


def _utc_timestamp() -> str:
    """Create a UTC ISO timestamp for synthesized replacement messages."""
    return datetime.now(timezone.utc).isoformat()


def resolve_replace_start(messages: list[ChatMessage], target_index: int) -> int:
    """Resolve where replacement should start for retry apply."""
    if target_index > 0 and messages[target_index - 1].role == "user":
        return target_index - 1
    return target_index


def build_retry_replacement_plan(
    messages: list[ChatMessage],
    target_index: int,
    retry_attempt: RetryAttempt,
    current_model: str,
    *,
    timestamp_factory: Optional[TimestampFactory] = None,
) -> RetryReplacementPlan:
    """Build a deterministic replacement plan for one retry attempt."""
    if target_index < 0 or target_index >= len(messages):
        raise ValueError("Retry target is no longer valid")

    make_timestamp = timestamp_factory or _utc_timestamp
    replace_start = resolve_replace_start(messages, target_index)

    existing_user_hex_id = (
        messages[replace_start].hex_id
        if replace_start != target_index
        else None
    )
    existing_assistant_hex_id = messages[target_index].hex_id

    user_msg = ChatMessage(
        timestamp_utc=make_timestamp(),
        role="user",
        content=text_to_lines(retry_attempt.user_msg),
        hex_id=existing_user_hex_id if isinstance(existing_user_hex_id, str) else None,
    )

    assistant_msg = ChatMessage(
        timestamp_utc=make_timestamp(),
        role="assistant",
        model=current_model,
        content=text_to_lines(retry_attempt.assistant_msg),
        citations=retry_attempt.citations,
        hex_id=existing_assistant_hex_id if isinstance(existing_assistant_hex_id, str) else None,
    )

    return RetryReplacementPlan(
        replace_start=replace_start,
        replace_end=target_index,
        replacement_messages=[user_msg, assistant_msg],
    )


class CommandSignalHandlersMixin(ChatSwitchingHandlersMixin):
    """Mixin implementing command-signal flow handlers for orchestrator."""

    manager: SessionManager

    def _signal_handlers(self) -> dict[str, SignalDispatchHandler]:
        """Return command-signal dispatch table."""
        return {
            "exit": self._dispatch_exit,
            "new_chat": self._dispatch_new_chat,
            "open_chat": self._dispatch_open_chat,
            "close_chat": self._dispatch_close_chat,
            "rename_current": self._dispatch_rename_current,
            "delete_current": self._dispatch_delete_current,
            "apply_retry": self._dispatch_apply_retry,
            "cancel_retry": self._dispatch_cancel_retry,
            "clear_secret_context": self._dispatch_clear_secret_context,
        }

    async def _handle_command_signal(
        self,
        signal: CommandSignal,
        *,
        current_chat_path: Optional[str],
        current_chat_data: Optional[ChatDocument],
    ) -> OrchestratorAction:
        """Handle typed command-layer control signals."""
        handler = self._signal_handlers().get(signal.kind)
        if handler is None:
            return PrintAction(message=f"Error: Unknown command signal '{signal.kind}'")
        return await handler(signal, current_chat_path, current_chat_data)

    async def _dispatch_exit(
        self,
        signal: CommandSignal,
        current_chat_path: Optional[str],
        current_chat_data: Optional[ChatDocument],
    ) -> OrchestratorAction:
        del signal, current_chat_path, current_chat_data
        return BreakAction()

    async def _dispatch_new_chat(
        self,
        signal: CommandSignal,
        current_chat_path: Optional[str],
        current_chat_data: Optional[ChatDocument],
    ) -> OrchestratorAction:
        if not signal.chat_path:
            return PrintAction(message="Error: Invalid command signal (missing new chat path)")
        return await self._handle_new_chat(signal.chat_path, current_chat_path, current_chat_data)

    async def _dispatch_open_chat(
        self,
        signal: CommandSignal,
        current_chat_path: Optional[str],
        current_chat_data: Optional[ChatDocument],
    ) -> OrchestratorAction:
        if not signal.chat_path:
            return PrintAction(message="Error: Invalid command signal (missing open chat path)")
        return await self._handle_open_chat(signal.chat_path, current_chat_path, current_chat_data)

    async def _dispatch_close_chat(
        self,
        signal: CommandSignal,
        current_chat_path: Optional[str],
        current_chat_data: Optional[ChatDocument],
    ) -> OrchestratorAction:
        del signal
        return await self._handle_close_chat(current_chat_path, current_chat_data)

    async def _dispatch_rename_current(
        self,
        signal: CommandSignal,
        current_chat_path: Optional[str],
        current_chat_data: Optional[ChatDocument],
    ) -> OrchestratorAction:
        del current_chat_path, current_chat_data
        if not signal.chat_path:
            return PrintAction(message="Error: Invalid command signal (missing rename path)")
        return self._handle_rename_current(signal.chat_path)

    async def _dispatch_delete_current(
        self,
        signal: CommandSignal,
        current_chat_path: Optional[str],
        current_chat_data: Optional[ChatDocument],
    ) -> OrchestratorAction:
        if signal.value is None:
            return PrintAction(message="Error: Invalid command signal (missing deleted filename)")
        return await self._handle_delete_current(
            signal.value,
            current_chat_path,
            current_chat_data,
        )

    async def _dispatch_apply_retry(
        self,
        signal: CommandSignal,
        current_chat_path: Optional[str],
        current_chat_data: Optional[ChatDocument],
    ) -> OrchestratorAction:
        retry_hex_id = (signal.value or "").strip().lower()
        if not retry_hex_id:
            return PrintAction(message="Retry ID not found")
        return await self._handle_apply_retry(current_chat_path, current_chat_data, retry_hex_id)

    async def _dispatch_cancel_retry(
        self,
        signal: CommandSignal,
        current_chat_path: Optional[str],
        current_chat_data: Optional[ChatDocument],
    ) -> OrchestratorAction:
        del signal, current_chat_path, current_chat_data
        return self._handle_cancel_retry()

    async def _dispatch_clear_secret_context(
        self,
        signal: CommandSignal,
        current_chat_path: Optional[str],
        current_chat_data: Optional[ChatDocument],
    ) -> OrchestratorAction:
        del signal, current_chat_path, current_chat_data
        return self._handle_clear_secret_context()

    async def _persist_chat_after_command(
        self,
        chat_path: Optional[str],
        chat_data: Optional[ChatDocument],
    ) -> None:
        """Persist chat after a command response when required by save policy."""
        await self.manager.save_current_chat(chat_path=chat_path, chat_data=chat_data)

    async def _handle_apply_retry(
        self,
        current_chat_path: Optional[str],
        current_chat_data: Optional[ChatDocument],
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

        messages = current_chat_data.messages
        target_index = self.manager.get_retry_target_index()
        if target_index is None or target_index < 0 or target_index >= len(messages):
            return PrintAction(message="Retry target is no longer valid")

        replacement_plan = build_retry_replacement_plan(
            messages,
            target_index,
            retry_attempt,
            self.manager.current_model,
        )
        messages[replacement_plan.replace_start : replacement_plan.replace_end + 1] = (
            replacement_plan.replacement_messages
        )

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
