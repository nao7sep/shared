"""Chat orchestration - handles lifecycle, modes, and command signals.

This module provides ChatOrchestrator which coordinates chat operations and state
transitions, decoupling this logic from the REPL loop. The orchestrator processes
command responses (signals) and user messages, returning actions for the REPL to execute.
"""

from dataclasses import dataclass
from typing import Optional, Any

from .session_manager import SessionManager
from . import chat
from .logging_utils import log_event


@dataclass
class OrchestratorAction:
    """Result of orchestration that tells REPL what to do.

    Attributes:
        action: Type of action to take ("continue", "break", "print", "error", "send_normal", "send_retry", "send_secret")
        message: Optional message to display to user
        chat_path: Optional new chat path (for chat switching)
        chat_data: Optional new chat data (for chat switching)
        error: Optional error information
        messages: Optional messages to send to AI
        mode: Optional mode string ("normal", "retry", "secret", "secret_oneshot")
    """
    action: str  # "continue", "break", "print", "error", "send_normal", "send_retry", "send_secret"
    message: Optional[str] = None
    chat_path: Optional[str] = None
    chat_data: Optional[dict] = None
    error: Optional[str] = None
    messages: Optional[list] = None
    mode: Optional[str] = None


class ChatOrchestrator:
    """Orchestrates chat lifecycle, mode transitions, and command signal processing.

    This class encapsulates the complex orchestration logic that was previously
    embedded in repl.py's main loop. It processes command signals (like __NEW_CHAT__,
    __OPEN_CHAT__, __APPLY_RETRY__, etc.) and user messages in different modes
    (normal, retry, secret), returning structured actions for the REPL to execute.

    Example:
        orchestrator = ChatOrchestrator(session_manager)

        # Handle command response
        action = await orchestrator.handle_command_response(
            "__NEW_CHAT__:/path/to/chat.json",
            current_chat_path="/old/chat.json",
            current_chat_data=old_chat
        )

        if action.action == "continue":
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
        response: str,
        current_chat_path: Optional[str],
        current_chat_data: Optional[dict]
    ) -> OrchestratorAction:
        """Process command response signal and return action for REPL.

        Handles special command signals like:
        - __EXIT__: Exit application
        - __NEW_CHAT__:<path>: Create and switch to new chat
        - __OPEN_CHAT__:<path>: Open existing chat
        - __CLOSE_CHAT__: Close current chat
        - __RENAME_CURRENT__:<new_path>: Rename current chat file
        - __DELETE_CURRENT__:<filename>: Delete current chat
        - __APPLY_RETRY__: Apply current retry attempt
        - __CANCEL_RETRY__: Cancel retry mode
        - __CLEAR_SECRET_CONTEXT__: Clear secret mode context
        - __SECRET_ONESHOT__:<message>: Handle one-shot secret question

        Args:
            response: Command response (may be signal or regular message)
            current_chat_path: Path to current chat file (if any)
            current_chat_data: Current chat data (if any)

        Returns:
            OrchestratorAction describing what the REPL should do next
        """
        # Handle EXIT signal
        if response == "__EXIT__":
            return OrchestratorAction(action="break")

        # Handle NEW_CHAT signal
        if response.startswith("__NEW_CHAT__:"):
            return await self._handle_new_chat(response, current_chat_path, current_chat_data)

        # Handle OPEN_CHAT signal
        if response.startswith("__OPEN_CHAT__:"):
            return await self._handle_open_chat(response, current_chat_path, current_chat_data)

        # Handle CLOSE_CHAT signal
        if response == "__CLOSE_CHAT__":
            return await self._handle_close_chat(current_chat_path, current_chat_data)

        # Handle RENAME_CURRENT signal
        if response.startswith("__RENAME_CURRENT__:"):
            return self._handle_rename_current(response)

        # Handle DELETE_CURRENT signal
        if response.startswith("__DELETE_CURRENT__:"):
            return await self._handle_delete_current(response, current_chat_path, current_chat_data)

        # Handle APPLY_RETRY signal
        if response == "__APPLY_RETRY__":
            return await self._handle_apply_retry(current_chat_path, current_chat_data)

        # Handle CANCEL_RETRY signal
        if response == "__CANCEL_RETRY__":
            return self._handle_cancel_retry()

        # Handle CLEAR_SECRET_CONTEXT signal
        if response == "__CLEAR_SECRET_CONTEXT__":
            return self._handle_clear_secret_context()

        # Handle SECRET_ONESHOT signal
        if response.startswith("__SECRET_ONESHOT__:"):
            return OrchestratorAction(
                action="secret_oneshot",
                message=response.split(":", 1)[1]
            )

        # Not a signal - print as regular message
        return OrchestratorAction(action="print", message=response)

    async def _handle_new_chat(
        self,
        signal: str,
        current_chat_path: Optional[str],
        current_chat_data: Optional[dict]
    ) -> OrchestratorAction:
        """Handle __NEW_CHAT__ signal."""
        new_chat_path = signal.split(":", 1)[1]

        # Save current chat before switching
        if current_chat_path and current_chat_data:
            await chat.save_chat(current_chat_path, current_chat_data)

        # Load new chat
        new_chat_data = chat.load_chat(new_chat_path)

        # Update session manager
        self.manager.switch_chat(new_chat_path, new_chat_data)

        log_event("chat_switch", chat_file=new_chat_path, trigger="new")

        return OrchestratorAction(
            action="continue",
            message=f"Created new chat: {new_chat_path}",
            chat_path=new_chat_path,
            chat_data=new_chat_data
        )

    async def _handle_open_chat(
        self,
        signal: str,
        current_chat_path: Optional[str],
        current_chat_data: Optional[dict]
    ) -> OrchestratorAction:
        """Handle __OPEN_CHAT__ signal."""
        new_chat_path = signal.split(":", 1)[1]

        # Save current chat before switching
        if current_chat_path and current_chat_data:
            await chat.save_chat(current_chat_path, current_chat_data)

        # Load selected chat
        new_chat_data = chat.load_chat(new_chat_path)

        # Update session manager
        self.manager.switch_chat(new_chat_path, new_chat_data)

        log_event("chat_switch", chat_file=new_chat_path, trigger="open")

        return OrchestratorAction(
            action="continue",
            message=f"Opened chat: {new_chat_path}",
            chat_path=new_chat_path,
            chat_data=new_chat_data
        )

    async def _handle_close_chat(
        self,
        current_chat_path: Optional[str],
        current_chat_data: Optional[dict]
    ) -> OrchestratorAction:
        """Handle __CLOSE_CHAT__ signal."""
        # Save current chat before closing
        if current_chat_path and current_chat_data:
            await chat.save_chat(current_chat_path, current_chat_data)

        # Clear chat in session manager
        self.manager.close_chat()

        log_event("chat_close", chat_file=current_chat_path)

        return OrchestratorAction(
            action="continue",
            message="Chat closed",
            chat_path=None,
            chat_data={}
        )

    def _handle_rename_current(self, signal: str) -> OrchestratorAction:
        """Handle __RENAME_CURRENT__ signal."""
        new_chat_path = signal.split(":", 1)[1]
        self.manager.chat_path = new_chat_path

        log_event("chat_rename", chat_file=new_chat_path)

        return OrchestratorAction(
            action="continue",
            message=f"Renamed to: {new_chat_path}",
            chat_path=new_chat_path
        )

    async def _handle_delete_current(
        self,
        signal: str,
        current_chat_path: Optional[str],
        current_chat_data: Optional[dict]
    ) -> OrchestratorAction:
        """Handle __DELETE_CURRENT__ signal."""
        deleted_filename = signal.split(":", 1)[1]

        # Clear chat in session manager
        self.manager.close_chat()

        log_event("chat_delete", chat_file=current_chat_path)

        return OrchestratorAction(
            action="continue",
            message=f"Deleted: {deleted_filename}",
            chat_path=None,
            chat_data={}
        )

    async def _handle_apply_retry(
        self,
        current_chat_path: Optional[str],
        current_chat_data: Optional[dict]
    ) -> OrchestratorAction:
        """Handle __APPLY_RETRY__ signal."""
        if not self.manager.retry_mode:
            return OrchestratorAction(action="print", message="Not in retry mode")

        if not current_chat_data:
            return OrchestratorAction(action="print", message="No chat open")

        # Get retry attempt messages
        user_msg, assistant_msg = self.manager.get_retry_attempt()

        if not user_msg or not assistant_msg:
            return OrchestratorAction(action="print", message="No retry attempt to apply")

        messages = current_chat_data.get("messages", [])

        # Remove last 2 messages (original user + assistant)
        if len(messages) >= 2:
            last_index = len(messages) - 1
            self.manager.remove_message_hex_id(last_index)
            last_index = len(messages) - 2
            self.manager.remove_message_hex_id(last_index)
            messages[:] = messages[:-2]

        # Add retry messages
        chat.add_user_message(current_chat_data, user_msg)
        new_msg_index = len(messages) - 1
        self.manager.assign_message_hex_id(new_msg_index)

        chat.add_assistant_message(
            current_chat_data, assistant_msg, self.manager.current_model
        )
        new_msg_index = len(messages) - 1
        self.manager.assign_message_hex_id(new_msg_index)

        # Save chat and exit retry mode
        if current_chat_path:
            await chat.save_chat(current_chat_path, current_chat_data)

        self.manager.exit_retry_mode()

        return OrchestratorAction(action="print", message="Applied retry - messages updated")

    def _handle_cancel_retry(self) -> OrchestratorAction:
        """Handle __CANCEL_RETRY__ signal."""
        if not self.manager.retry_mode:
            return OrchestratorAction(action="print", message="Not in retry mode")

        self.manager.exit_retry_mode()

        return OrchestratorAction(action="print", message="Cancelled retry mode")

    def _handle_clear_secret_context(self) -> OrchestratorAction:
        """Handle __CLEAR_SECRET_CONTEXT__ signal."""
        if self.manager.secret_mode:
            self.manager.exit_secret_mode()
            return OrchestratorAction(action="print", message="Secret mode disabled")

        return OrchestratorAction(action="continue")

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
            return OrchestratorAction(
                action="print",
                message="\nNo chat is currently open.\nUse /new to create a new chat or /open to open an existing one."
            )

        # Check for pending error
        from .app_state import has_pending_error
        if has_pending_error(chat_data):
            return OrchestratorAction(
                action="print",
                message="\n⚠️  Cannot continue - last interaction resulted in an error.\nUse /retry to retry the last message, /secret to ask without saving,\nor /rewind to remove the error and continue from an earlier point."
            )

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
        # Enter secret mode if not already (freeze context)
        try:
            secret_context = self.manager.get_secret_context()
        except ValueError:
            # Not in secret mode yet, freeze context
            secret_context = chat.get_messages_for_ai(chat_data)
            self.manager.enter_secret_mode(secret_context)
            secret_context = self.manager.get_secret_context()

        # Prepare temporary messages (not saved)
        temp_messages = secret_context + [{"role": "user", "content": user_input}]

        return OrchestratorAction(
            action="send_secret",
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

        return OrchestratorAction(
            action="send_retry",
            messages=temp_messages,
            mode="retry",
            message=user_input,  # Store for set_retry_attempt
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

        return OrchestratorAction(
            action="send_normal",
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
        mode: str,
        user_input: Optional[str] = None,
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
            # Store retry attempt
            if user_input:
                self.manager.set_retry_attempt(user_input, response_text)
            return OrchestratorAction(action="continue")

        elif mode == "secret":
            # Secret messages not saved
            return OrchestratorAction(action="continue")

        elif mode == "normal":
            # Add assistant message and save
            chat.add_assistant_message(chat_data, response_text, self.manager.current_model)
            new_msg_index = len(chat_data["messages"]) - 1
            self.manager.assign_message_hex_id(new_msg_index)
            await chat.save_chat(chat_path, chat_data)
            return OrchestratorAction(action="continue")

        return OrchestratorAction(action="continue")

    async def handle_ai_error(
        self,
        error: Exception,
        chat_path: str,
        chat_data: dict,
        mode: str,
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
            # Remove the user message that was added
            if chat_data["messages"] and chat_data["messages"][-1]["role"] == "user":
                last_index = len(chat_data["messages"]) - 1
                chat_data["messages"].pop()
                self.manager.remove_message_hex_id(last_index)

            # Add error message
            sanitized_error = sanitize_error_message(str(error))
            chat.add_error_message(
                chat_data,
                sanitized_error,
                {"provider": self.manager.current_ai, "model": self.manager.current_model},
            )
            new_msg_index = len(chat_data["messages"]) - 1
            self.manager.assign_message_hex_id(new_msg_index)
            await chat.save_chat(chat_path, chat_data)

        # For retry and secret modes, just show error (don't save)
        return OrchestratorAction(action="print", message=f"\nError: {error}")

    async def handle_user_cancel(
        self,
        chat_data: dict,
        mode: str,
    ) -> OrchestratorAction:
        """Handle user cancellation (KeyboardInterrupt during AI response).

        Args:
            chat_data: Chat data
            mode: Mode that was used ("normal", "retry", "secret")

        Returns:
            OrchestratorAction for next step
        """
        if mode == "normal":
            # Remove the user message that was added
            if chat_data["messages"] and chat_data["messages"][-1]["role"] == "user":
                last_index = len(chat_data["messages"]) - 1
                chat_data["messages"].pop()
                self.manager.remove_message_hex_id(last_index)

        # For retry and secret modes, nothing to clean up
        return OrchestratorAction(action="print", message="\n[Message cancelled]")
