"""Command-signal handling helpers for chat orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Awaitable, Callable, Optional

from ..chat import LastInteractionSpan
from ..commands.types import CommandSignal
from ..domain.chat import ChatMessage, RetryAttempt
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
    [CommandSignal],
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


def build_retry_replacement_plan(
    messages: list[ChatMessage],
    target_span: LastInteractionSpan,
    retry_attempt: RetryAttempt,
    current_model: str,
    *,
    generated_user_hex_id: str | None = None,
    timestamp_factory: Optional[TimestampFactory] = None,
) -> RetryReplacementPlan:
    """Build a deterministic replacement plan for one retry attempt."""
    if (
        target_span.replace_start < 0
        or target_span.replace_end < target_span.replace_start
        or target_span.replace_end >= len(messages)
    ):
        raise ValueError("Retry target is no longer valid")

    make_timestamp = timestamp_factory or _utc_timestamp
    existing_user_hex_id = None
    if target_span.kind != "standalone_error":
        existing_user_hex_id = messages[target_span.replace_start].hex_id
    existing_assistant_hex_id = messages[target_span.replace_end].hex_id

    if target_span.kind == "standalone_error" and generated_user_hex_id is None:
        raise ValueError("Standalone error retries require a generated user hex ID")

    user_msg = ChatMessage(
        timestamp_utc=make_timestamp(),
        role="user",
        content=text_to_lines(retry_attempt.user_msg),
        hex_id=(
            generated_user_hex_id
            if target_span.kind == "standalone_error"
            else existing_user_hex_id if isinstance(existing_user_hex_id, str) else None
        ),
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
        replace_start=target_span.replace_start,
        replace_end=target_span.replace_end,
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
    ) -> OrchestratorAction:
        """Handle typed command-layer control signals."""
        handler = self._signal_handlers().get(signal.kind)
        if handler is None:
            return PrintAction(message=f"Error: Unknown command signal '{signal.kind}'")
        return await handler(signal)

    async def _dispatch_exit(
        self,
        signal: CommandSignal,
    ) -> OrchestratorAction:
        del signal
        return BreakAction()

    async def _dispatch_new_chat(
        self,
        signal: CommandSignal,
    ) -> OrchestratorAction:
        if not signal.chat_path:
            return PrintAction(message="Error: Invalid command signal (missing new chat path)")
        return await self._handle_new_chat(signal.chat_path)

    async def _dispatch_open_chat(
        self,
        signal: CommandSignal,
    ) -> OrchestratorAction:
        if not signal.chat_path:
            return PrintAction(message="Error: Invalid command signal (missing open chat path)")
        return await self._handle_open_chat(signal.chat_path)

    async def _dispatch_close_chat(
        self,
        signal: CommandSignal,
    ) -> OrchestratorAction:
        del signal
        return await self._handle_close_chat()

    async def _dispatch_rename_current(
        self,
        signal: CommandSignal,
    ) -> OrchestratorAction:
        if not signal.chat_path:
            return PrintAction(message="Error: Invalid command signal (missing rename path)")
        return self._handle_rename_current(signal.chat_path)

    async def _dispatch_delete_current(
        self,
        signal: CommandSignal,
    ) -> OrchestratorAction:
        if signal.value is None:
            return PrintAction(message="Error: Invalid command signal (missing deleted filename)")
        return await self._handle_delete_current(signal.value)

    async def _dispatch_apply_retry(
        self,
        signal: CommandSignal,
    ) -> OrchestratorAction:
        retry_hex_id = (signal.value or "").strip().lower()
        if not retry_hex_id:
            return PrintAction(message="Retry ID not found")
        return await self._handle_apply_retry(retry_hex_id)

    async def _dispatch_cancel_retry(
        self,
        signal: CommandSignal,
    ) -> OrchestratorAction:
        del signal
        return self._handle_cancel_retry()

    async def _dispatch_clear_secret_context(
        self,
        signal: CommandSignal,
    ) -> OrchestratorAction:
        del signal
        return self._handle_clear_secret_context()

    async def _persist_chat_after_command(self) -> None:
        """Persist chat after a command response when required by save policy."""
        await self.manager.save_current_chat(
            chat_path=self.manager.chat_path,
            chat_data=self.manager.chat,
        )

    async def _handle_apply_retry(
        self,
        retry_hex_id: str,
    ) -> OrchestratorAction:
        """Handle apply-retry signal."""
        if not self.manager.retry.active:
            return PrintAction(message="Not in retry mode")

        chat_data = self.manager.chat
        chat_path = self.manager.chat_path

        if not chat_data:
            return PrintAction(message="No chat open")

        retry_attempt = self.manager.retry.get_attempt(retry_hex_id)
        if not retry_attempt:
            return PrintAction(message=f"Retry ID not found: {retry_hex_id}")

        messages = chat_data.messages
        target_span = self.manager.retry.target_span
        if target_span is None or target_span.replace_end >= len(messages):
            return PrintAction(message="Retry target is no longer valid")

        generated_user_hex_id = None
        if target_span.kind == "standalone_error":
            generated_user_hex_id = self.manager.reserve_hex_id()

        try:
            replacement_plan = build_retry_replacement_plan(
                messages,
                target_span,
                retry_attempt,
                self.manager.current_model,
                generated_user_hex_id=generated_user_hex_id,
            )
        except Exception:
            if generated_user_hex_id is not None:
                self.manager.release_hex_id(generated_user_hex_id)
            raise
        messages[replacement_plan.replace_start : replacement_plan.replace_end + 1] = (
            replacement_plan.replacement_messages
        )

        if chat_path:
            await self.manager.save_current_chat(
                chat_path=chat_path,
                chat_data=chat_data,
            )

        self.manager.retry.exit()

        return PrintAction(message=f"Applied retry [{retry_hex_id}]")

    def _handle_cancel_retry(self) -> OrchestratorAction:
        """Handle cancel-retry signal."""
        if not self.manager.retry.active:
            return PrintAction(message="Not in retry mode")

        self.manager.retry.exit()

        return PrintAction(message="Cancelled retry mode")

    def _handle_clear_secret_context(self) -> OrchestratorAction:
        """Handle clear-secret-context signal."""
        if self.manager.secret.active:
            self.manager.secret.exit()
            return PrintAction(message="Secret mode disabled")

        return ContinueAction()
