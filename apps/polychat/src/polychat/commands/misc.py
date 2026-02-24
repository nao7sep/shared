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


class MiscCommandsMixin(_CommandDependencies):
    """Legacy adapter exposing misc commands on CommandHandler."""

    _misc_commands: MiscCommandHandlers

    async def show_help(self, args: str) -> str:
        return await self._misc_commands.show_help(args)

    async def exit_app(self, args: str) -> CommandResult:
        return await self._misc_commands.exit_app(args)
