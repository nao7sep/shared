"""Command system façade for PolyChat."""

from typing import Optional

from ..chat import save_chat
from ..helper_ai import invoke_helper_ai
from .base import CommandHandlerBaseMixin
from .runtime import RuntimeCommandsMixin
from .metadata import MetadataCommandsMixin
from .chat_files import ChatFileCommandsMixin
from .misc import MiscCommandsMixin


class CommandHandler(
    CommandHandlerBaseMixin,
    RuntimeCommandsMixin,
    MetadataCommandsMixin,
    ChatFileCommandsMixin,
    MiscCommandsMixin,
):
    """Handles command parsing and execution."""

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

        if command in ["gpt", "gem", "cla", "grok", "perp", "mist", "deep"]:
            return self.switch_provider_shortcut(command)

        command_map = {
            "model": self.set_model,
            "helper": self.set_helper,
            "input": self.set_input_mode,
            "timeout": self.set_timeout,
            "system": self.set_system_prompt,
            "retry": self.retry_mode,
            "apply": self.apply_retry,
            "cancel": self.cancel_retry,
            "secret": self.secret_mode_command,
            "search": self.search_mode_command,
            "rewind": self.rewind_messages,
            "purge": self.purge_messages,
            "history": self.show_history,
            "show": self.show_message,
            "status": self.show_status,
            "title": self.set_title,
            "summary": self.set_summary,
            "safe": self.check_safety,
            "new": self.new_chat,
            "open": self.open_chat,
            "switch": self.switch_chat,
            "close": self.close_chat,
            "rename": self.rename_chat_file,
            "delete": self.delete_chat_command,
            "help": self.show_help,
            "exit": self.exit_app,
            "quit": self.exit_app,
        }

        if command in command_map:
            return await command_map[command](args)

        raise ValueError(f"Unknown command: /{command}")


__all__ = ["CommandHandler", "save_chat", "invoke_helper_ai"]
