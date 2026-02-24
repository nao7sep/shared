"""Command system façade for PolyChat."""

from typing import Optional, TYPE_CHECKING

from ..chat import save_chat
from ..ai.helper_runtime import invoke_helper_ai
from .base import CommandHandlerBaseMixin
from .dispatcher import CommandDispatcher
from .runtime import RuntimeCommandsMixin
from .metadata import MetadataCommandsMixin
from .chat_files import ChatFileCommandsMixin
from .misc import MiscCommandsMixin
from .types import CommandResult
from ..ui.interaction import UserInteractionPort

if TYPE_CHECKING:
    from ..session_manager import SessionManager


class CommandHandler(
    CommandHandlerBaseMixin,
    RuntimeCommandsMixin,
    MetadataCommandsMixin,
    ChatFileCommandsMixin,
    MiscCommandsMixin,
):
    """Handles command parsing and execution."""

    def __init__(
        self,
        manager: "SessionManager",
        interaction: Optional[UserInteractionPort] = None,
    ) -> None:
        super().__init__(manager, interaction=interaction)
        self._dispatcher = CommandDispatcher(self)

    async def execute_command(self, text: str) -> CommandResult:
        """Execute a command.

        Args:
            text: Command text

        Returns:
            Command result (text output, control signal, or None)

        Raises:
            ValueError: If command is invalid
        """
        command, args = self.parse_command(text)

        if not command:
            raise ValueError("Empty command")

        return await self._dispatcher.dispatch(command, args)


__all__ = ["CommandHandler", "save_chat", "invoke_helper_ai"]
