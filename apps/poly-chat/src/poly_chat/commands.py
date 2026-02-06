"""Command system for PolyChat.

This module handles parsing and executing commands like /model, /gpt, /retry, etc.
"""

from typing import Optional, Any
from . import models
from .chat import (
    update_metadata,
    delete_message_and_following,
    save_chat,
)


class CommandHandler:
    """Handles command parsing and execution."""

    def __init__(self, session_state: dict[str, Any]):
        """Initialize command handler.

        Args:
            session_state: Dictionary containing session state
                - current_ai: Current AI provider
                - current_model: Current model
                - profile: Profile dict
                - conversation: Conversation dict
        """
        self.session = session_state

    def is_command(self, text: str) -> bool:
        """Check if text is a command.

        Args:
            text: User input text

        Returns:
            True if text starts with /
        """
        return text.strip().startswith("/")

    def parse_command(self, text: str) -> tuple[str, str]:
        """Parse command text into command and arguments.

        Args:
            text: Command text (e.g., "/model gpt-5-mini")

        Returns:
            Tuple of (command, args) where command is without / and args is the rest
        """
        text = text.strip()
        if not text.startswith("/"):
            return "", ""

        parts = text[1:].split(None, 1)
        command = parts[0] if parts else ""
        args = parts[1] if len(parts) > 1 else ""

        return command, args

    async def execute_command(self, text: str) -> Optional[str]:
        """Execute a command.

        Args:
            text: Command text

        Returns:
            Response message, or None if command modifies state silently

        Raises:
            ValueError: If command is invalid
        """
        command, args = self.parse_command(text)

        if not command:
            raise ValueError("Empty command")

        # Provider shortcuts
        if command in ["gpt", "gem", "cla", "grok", "perp", "mist", "deep"]:
            return self.switch_provider_shortcut(command)

        # Other commands
        command_map = {
            "model": self.set_model,
            "timeout": self.set_timeout,
            "retry": self.retry_mode,
            "delete": self.delete_messages,
            "title": self.set_title,
            "ai-title": self.generate_title,
            "summary": self.set_summary,
            "ai-summary": self.generate_summary,
            "safe": self.check_safety,
            "help": self.show_help,
            "exit": self.exit_app,
            "quit": self.exit_app,
        }

        if command in command_map:
            return await command_map[command](args)
        else:
            raise ValueError(f"Unknown command: /{command}")

    def switch_provider_shortcut(self, shortcut: str) -> str:
        """Switch AI provider using shortcut.

        Args:
            shortcut: Provider shortcut (gpt, gem, cla, etc.)

        Returns:
            Confirmation message
        """
        provider = models.resolve_provider_shortcut(shortcut)
        if not provider:
            raise ValueError(f"Unknown provider shortcut: /{shortcut}")

        # Get model for this provider from profile
        model = self.session["profile"]["models"].get(provider)
        if not model:
            raise ValueError(f"No model configured for {provider}")

        self.session["current_ai"] = provider
        self.session["current_model"] = model

        return f"Switched to {provider} ({model})"

    async def set_model(self, args: str) -> str:
        """Set the current model.

        Args:
            args: Model name or empty to show list

        Returns:
            Confirmation message or model list
        """
        if not args:
            # Show available models for current provider
            provider = self.session["current_ai"]
            available_models = models.get_models_for_provider(provider)
            return f"Available models for {provider}:\n" + "\n".join(
                f"  - {m}" for m in available_models
            )

        # Check if model exists and switch provider if needed
        provider = models.get_provider_for_model(args)
        if provider:
            self.session["current_ai"] = provider
            self.session["current_model"] = args
            return f"Switched to {provider} ({args})"
        else:
            # Model not in registry, but allow it anyway (might be new)
            self.session["current_model"] = args
            return f"Set model to {args} (provider: {self.session['current_ai']})"

    async def set_timeout(self, args: str) -> str:
        """Set or show the timeout setting.

        Args:
            args: Timeout in seconds or empty to show current

        Returns:
            Confirmation message or current timeout
        """
        if not args:
            # Show current timeout
            timeout = self.session["profile"].get("timeout", 30)
            if timeout == 0:
                return "Current timeout: 0 (wait forever)"
            else:
                return f"Current timeout: {timeout} seconds"

        # Parse and set timeout
        try:
            timeout = float(args)
            if timeout < 0:
                raise ValueError("Timeout must be non-negative")

            self.session["profile"]["timeout"] = timeout

            # Clear provider cache since timeout changed
            if "_provider_cache" in self.session:
                self.session["_provider_cache"].clear()

            if timeout == 0:
                return "Timeout set to 0 (wait forever). Provider cache cleared."
            else:
                return f"Timeout set to {timeout} seconds. Provider cache cleared."

        except ValueError:
            raise ValueError("Invalid timeout value. Use a number (e.g., /timeout 60) or 0 for no timeout.")

    async def retry_mode(self, args: str) -> str:
        """Enter retry mode (ask again without saving previous attempt).

        Args:
            args: Not used

        Returns:
            Info message
        """
        chat = self.session["conversation"]
        messages = chat["messages"]

        # Check if there's an assistant message to retry
        if not messages:
            return "No messages to retry"

        last_msg = messages[-1]
        if last_msg["role"] != "assistant":
            return "Last message is not an assistant response. Nothing to retry."

        # Set retry mode flag - the REPL loop will handle the actual replacement
        self.session["retry_mode"] = True
        return "Retry mode enabled. Your next message will replace the last assistant response."

    async def delete_messages(self, args: str) -> str:
        """Delete message and all following messages.

        Args:
            args: Message index (0-based) or "last" to delete last message

        Returns:
            Confirmation message
        """
        chat = self.session["conversation"]
        messages = chat["messages"]

        if not messages:
            return "No messages to delete"

        if args == "last":
            index = len(messages) - 1
        else:
            try:
                index = int(args)
            except ValueError:
                raise ValueError("Invalid message index. Use a number or 'last'")

        try:
            count = delete_message_and_following(chat, index)
            # Save chat history after deletion
            chat_path = self.session.get("chat_path")
            if chat_path:
                await save_chat(chat_path, chat)
            return f"Deleted {count} message(s) from index {index} onwards"
        except IndexError:
            raise ValueError(
                f"Message index {index} out of range (0-{len(messages)-1})"
            )

    async def set_title(self, args: str) -> str:
        """Set chat title.

        Args:
            args: Title text or empty to clear

        Returns:
            Confirmation message
        """
        chat = self.session["conversation"]

        if not args:
            # Clear title
            update_metadata(chat, title=None)
            return "Title cleared"
        else:
            update_metadata(chat, title=args)
            return f"Title set to: {args}"

    async def generate_title(self, args: str) -> str:
        """Generate title using AI.

        Args:
            args: Not used

        Returns:
            Generated title or error message
        """
        # This would need AI call to generate title
        # For now, return placeholder
        return "AI title generation not yet implemented"

    async def set_summary(self, args: str) -> str:
        """Set chat summary.

        Args:
            args: Summary text or empty to clear

        Returns:
            Confirmation message
        """
        chat = self.session["conversation"]

        if not args:
            # Clear summary
            update_metadata(chat, summary=None)
            return "Summary cleared"
        else:
            update_metadata(chat, summary=args)
            return "Summary set"

    async def generate_summary(self, args: str) -> str:
        """Generate summary using AI.

        Args:
            args: Not used

        Returns:
            Generated summary or error message
        """
        # This would need AI call to generate summary
        # For now, return placeholder
        return "AI summary generation not yet implemented"

    async def check_safety(self, args: str) -> str:
        """Check chat for unsafe content.

        Args:
            args: Not used

        Returns:
            Safety check results
        """
        # This would need AI call to check safety
        # For now, return placeholder
        return "Safety check not yet implemented"

    async def show_help(self, args: str) -> str:
        """Show help information.

        Args:
            args: Not used

        Returns:
            Help text
        """
        return """
PolyChat Commands:

Provider Shortcuts:
  /gpt              Switch to OpenAI GPT
  /gem              Switch to Google Gemini
  /cla              Switch to Anthropic Claude
  /grok             Switch to xAI Grok
  /perp             Switch to Perplexity
  /mist             Switch to Mistral
  /deep             Switch to DeepSeek

Model Management:
  /model            Show available models for current provider
  /model <name>     Switch to specified model (auto-detects provider)

Configuration:
  /timeout          Show current timeout setting
  /timeout <secs>   Set timeout in seconds (0 = wait forever)

Chat Control:
  /retry            Replace last response (enter retry mode)
  /delete <index>   Delete message at index and all following
  /delete last      Delete last message

Metadata:
  /title <text>     Set chat title
  /title            Clear title
  /ai-title         Generate title using AI
  /summary <text>   Set chat summary
  /summary          Clear summary
  /ai-summary       Generate summary using AI

Other:
  /safe             Check chat for unsafe content
  /help             Show this help
  /exit, /quit      Exit PolyChat
"""

    async def exit_app(self, args: str) -> str:
        """Exit the application.

        Args:
            args: Not used

        Returns:
            Exit message (triggers exit in main loop)
        """
        return "__EXIT__"
