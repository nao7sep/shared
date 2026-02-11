"""Chat orchestration - handles lifecycle, modes, and command signals.

This module provides ChatOrchestrator which coordinates chat operations and state
transitions, decoupling this logic from the REPL loop. The orchestrator processes
command responses (signals) and user messages, returning actions for the REPL to execute.
"""

from datetime import datetime, timezone
from typing import Optional

from .session_manager import SessionManager
from . import chat
from .logging_utils import log_event
from .message_formatter import text_to_lines
from .commands.types import CommandResult, CommandSignal
from .orchestrator_types import (
    ActionMode,
    BreakAction,
    ContinueAction,
    OrchestratorAction,
    PrintAction,
    SendAction,
)


class ChatOrchestrator:
    """Orchestrates chat lifecycle, mode transitions, and command signal processing.

    This class encapsulates the complex orchestration logic that was previously
    embedded in repl.py's main loop. It processes typed command signals
    (exit/new_chat/open_chat/apply_retry/etc.) and user messages in different modes
    (normal, retry, secret), returning structured actions for the REPL to execute.

    Example:
        orchestrator = ChatOrchestrator(session_manager)

        # Handle command response
        action = await orchestrator.handle_command_response(
            CommandSignal(kind="new_chat", chat_path="/path/to/chat.json"),
            current_chat_path="/old/chat.json",
            current_chat_data=old_chat
        )

        if isinstance(action, ContinueAction):
            # Update chat path and data
            chat_path = action.chat_path
            chat_data = action.chat_data
    """

    def __init__(self, session_manager: SessionManager):
        """Initialize orchestrator.

        Args:
            session_manager: SessionManager instance for state access
        """
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
            await self._save_chat_if_dirty(current_chat_path, current_chat_data)
            return PrintAction(message=response)

        # Command handlers may intentionally return None for silent no-op.
        return ContinueAction()

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

        # Save current chat before switching
        if current_chat_path and current_chat_data:
            await self.manager.save_current_chat(
                force=True,
                chat_path=current_chat_path,
                chat_data=current_chat_data,
            )

        # Load new chat
        new_chat_data = chat.load_chat(new_chat_path)
        await self.manager.save_current_chat(
            force=True,
            chat_path=new_chat_path,
            chat_data=new_chat_data,
        )

        # Update session manager
        self.manager.switch_chat(new_chat_path, new_chat_data)

        log_event(
            "chat_switch",
            chat_file=new_chat_path,
            trigger="new",
            previous_chat_file=current_chat_path,
            message_count=len(new_chat_data.get("messages", [])),
        )

        return ContinueAction(
            message=f"Created new chat: {new_chat_path}",
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

        # Save current chat before switching
        if current_chat_path and current_chat_data:
            await self.manager.save_current_chat(
                force=True,
                chat_path=current_chat_path,
                chat_data=current_chat_data,
            )

        # Load selected chat
        new_chat_data = chat.load_chat(new_chat_path)

        # Update session manager
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
        # Save current chat before closing
        if current_chat_path and current_chat_data:
            await self.manager.save_current_chat(
                force=True,
                chat_path=current_chat_path,
                chat_data=current_chat_data,
            )

        # Clear chat in session manager
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

        # Clear chat in session manager
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

        existing_hex_id = messages[target_index].get("hex_id")
        replaced_message = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "role": "assistant",
            "model": self.manager.current_model,
            "content": text_to_lines(retry_attempt["assistant_msg"]),
        }
        citations = retry_attempt.get("citations")
        if citations:
            replaced_message["citations"] = citations
        if isinstance(existing_hex_id, str):
            replaced_message["hex_id"] = existing_hex_id
        messages[target_index] = replaced_message

        # Save chat and exit retry mode
        if current_chat_path:
            await self.manager.save_current_chat(
                force=True,
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

    # ===================================================================
    # User Message Handling
    # ===================================================================

    async def handle_user_message(
        self,
        user_input: str,
        chat_path: Optional[str],
        chat_data: Optional[dict],
    ) -> OrchestratorAction:
        """Process user message and return action for REPL.

        Determines the appropriate mode (normal, retry, secret) and prepares
        messages for AI invocation. The REPL is responsible for actual AI
        invocation, streaming display, and error handling.

        Args:
            user_input: User's input message
            chat_path: Path to current chat file (if any)
            chat_data: Current chat data (if any)

        Returns:
            OrchestratorAction describing what the REPL should do next
        """
        # Check if chat is open
        if not chat_path:
            return PrintAction(
                message=(
                    "\nNo chat is currently open.\n"
                    "Use /new to create a new chat or /open to open an existing one."
                )
            )

        # Check for pending error
        from .app_state import has_pending_error, pending_error_guidance
        if has_pending_error(chat_data) and not self.manager.retry_mode and not self.manager.secret_mode:
            return PrintAction(message=pending_error_guidance())

        # Handle secret mode
        if self.manager.secret_mode:
            return await self._handle_secret_message(user_input, chat_data)

        # Handle retry mode
        if self.manager.retry_mode:
            return await self._handle_retry_message(user_input, chat_data)

        # Handle normal message
        return await self._handle_normal_message(user_input, chat_data, chat_path)

    async def _handle_secret_message(
        self, user_input: str, chat_data: dict
    ) -> OrchestratorAction:
        """Handle message in secret mode."""
        # Always derive from persisted chat history; secret turns are never saved.
        secret_context = chat.get_messages_for_ai(chat_data)
        temp_messages = secret_context + [{"role": "user", "content": user_input}]

        return self._build_send_action(
            messages=temp_messages,
            mode="secret",
        )

    async def _handle_retry_message(
        self, user_input: str, chat_data: dict
    ) -> OrchestratorAction:
        """Handle message in retry mode."""
        # Enter retry mode if not already (freeze context)
        try:
            retry_context = self.manager.get_retry_context()
        except ValueError:
            # Not in retry mode yet, freeze context
            all_messages = chat.get_messages_for_ai(chat_data)
            if all_messages and all_messages[-1]["role"] == "assistant":
                self.manager.enter_retry_mode(all_messages[:-1])
            else:
                self.manager.enter_retry_mode(all_messages)
            retry_context = self.manager.get_retry_context()

        # Prepare temporary messages
        temp_messages = retry_context + [{"role": "user", "content": user_input}]

        return self._build_send_action(
            messages=temp_messages,
            mode="retry",
            retry_user_input=user_input,
            assistant_hex_id=self.manager.reserve_hex_id(),
        )

    async def _handle_normal_message(
        self, user_input: str, chat_data: dict, chat_path: str
    ) -> OrchestratorAction:
        """Handle normal message."""
        # Add user message to chat
        chat.add_user_message(chat_data, user_input)
        new_msg_index = len(chat_data["messages"]) - 1
        self.manager.assign_message_hex_id(new_msg_index)

        # Get messages for AI
        messages = chat.get_messages_for_ai(chat_data)

        return self._build_send_action(
            messages=messages,
            mode="normal",
            chat_path=chat_path,
            chat_data=chat_data,
        )

    async def handle_ai_response(
        self,
        response_text: str,
        chat_path: str,
        chat_data: dict,
        mode: ActionMode,
        user_input: Optional[str] = None,
        assistant_hex_id: Optional[str] = None,
        citations: Optional[list[dict]] = None,
        thoughts: Optional[str] = None,
    ) -> OrchestratorAction:
        """Handle successful AI response.

        Args:
            response_text: AI response text
            chat_path: Path to chat file
            chat_data: Chat data
            mode: Mode that was used ("normal", "retry", "secret")
            user_input: Original user input (for retry mode)

        Returns:
            OrchestratorAction for next step
        """
        if mode == "retry":
            # Store retry attempt and expose runtime hex ID so user can /apply <id>.
            if user_input and assistant_hex_id:
                self.manager.add_retry_attempt(
                    user_input,
                    response_text,
                    retry_hex_id=assistant_hex_id,
                    citations=citations,
                )
            return ContinueAction()

        elif mode == "secret":
            # Secret messages not saved
            if assistant_hex_id:
                self.manager.release_hex_id(assistant_hex_id)
            return ContinueAction()

        elif mode == "normal":
            # Add assistant message and save
            chat.add_assistant_message(
                chat_data,
                response_text,
                self.manager.current_model,
                citations=citations,
                thoughts=thoughts,
            )
            if chat_data.get("messages"):
                if assistant_hex_id:
                    chat_data["messages"][-1]["hex_id"] = assistant_hex_id
                else:
                    new_msg_index = len(chat_data["messages"]) - 1
                    self.manager.assign_message_hex_id(new_msg_index)
            await self.manager.save_current_chat(
                force=True,
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
        """Rollback pending state when provider validation fails pre-send."""
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
            force=True,
            chat_path=chat_path,
            chat_data=chat_data,
        )
        return True

    async def handle_ai_error(
        self,
        error: Exception,
        chat_path: str,
        chat_data: dict,
        mode: ActionMode,
        assistant_hex_id: Optional[str] = None,
    ) -> OrchestratorAction:
        """Handle AI error.

        Args:
            error: The exception that occurred
            chat_path: Path to chat file
            chat_data: Chat data
            mode: Mode that was used ("normal", "retry", "secret")

        Returns:
            OrchestratorAction for next step
        """
        from .logging_utils import sanitize_error_message

        if mode == "normal":
            if assistant_hex_id:
                self.manager.release_hex_id(assistant_hex_id)
            # Remove the user message that was added
            if chat_data["messages"] and chat_data["messages"][-1]["role"] == "user":
                self.manager.pop_message(-1, chat_data)

            # Add error message
            sanitized_error = sanitize_error_message(str(error))
            chat.add_error_message(
                chat_data,
                sanitized_error,
                {"provider": self.manager.current_ai, "model": self.manager.current_model},
            )
            new_msg_index = len(chat_data["messages"]) - 1
            self.manager.assign_message_hex_id(new_msg_index)
            await self.manager.save_current_chat(
                force=True,
                chat_path=chat_path,
                chat_data=chat_data,
            )
        elif assistant_hex_id:
            # For retry and secret modes, just release hex ID (don't save)
            self.manager.release_hex_id(assistant_hex_id)

        return PrintAction(message=f"\nError: {error}")

    async def handle_user_cancel(
        self,
        chat_data: dict,
        mode: ActionMode,
        chat_path: Optional[str] = None,
        assistant_hex_id: Optional[str] = None,
    ) -> OrchestratorAction:
        """Handle user cancellation (KeyboardInterrupt during AI response).

        Args:
            chat_data: Chat data
            mode: Mode that was used ("normal", "retry", "secret")

        Returns:
            OrchestratorAction for next step
        """
        if mode == "normal":
            if assistant_hex_id:
                self.manager.release_hex_id(assistant_hex_id)
            # Remove the user message that was added
            if chat_data["messages"] and chat_data["messages"][-1]["role"] == "user":
                self.manager.pop_message(-1, chat_data)
            await self.manager.save_current_chat(
                force=True,
                chat_path=chat_path,
                chat_data=chat_data,
            )

        # For retry and secret modes, nothing to clean up
        if mode in ("retry", "secret") and assistant_hex_id:
            self.manager.release_hex_id(assistant_hex_id)
        return PrintAction(message="\n[Message cancelled]")
