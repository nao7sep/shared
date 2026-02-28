"""Misc command handlers and compatibility adapters."""

from typing import TYPE_CHECKING

from .command_docs import render_help_text
from .types import CommandResult, CommandSignal

if TYPE_CHECKING:
    from .contracts import CommandDependencies as _CommandDependencies
else:
    class _CommandDependencies:
        pass

class MiscCommandHandlers:
    """Explicit handlers for help/exit commands."""

    async def show_help(self, args: str) -> str:
        """Show help information."""
        return render_help_text()

    async def exit_app(self, args: str) -> CommandResult:
        """Exit the application."""
        return CommandSignal(kind="exit")


