"""Command system façade for PolyChat."""

from typing import Optional, TYPE_CHECKING

from ..chat import save_chat
from ..ai.helper_runtime import invoke_helper_ai
from .base import CommandHandlerBaseMixin
from .context import HelperAIInvoker
from .dispatch import CommandDispatcher
from .runtime_models import RuntimeModelCommandHandlers, RuntimeModelCommandsMixin
from .runtime_modes import RuntimeModeCommandHandlers, RuntimeModeCommandsMixin
from .runtime_mutation import RuntimeMutationCommandHandlers, RuntimeMutationCommandsMixin
from .meta_generation import MetadataGenerationCommandHandlers, MetadataGenerationCommandsMixin
from .meta_inspection import MetadataInspectionCommandHandlers, MetadataInspectionCommandsMixin
from .chat_files import ChatFileCommandHandlers, ChatFileCommandsMixin
from .misc import MiscCommandHandlers, MiscCommandsMixin
from .types import CommandResult
from ..ui.interaction import UserInteractionPort

if TYPE_CHECKING:
    from ..session_manager import SessionManager


class CommandHandler(
    CommandHandlerBaseMixin,
    RuntimeModelCommandsMixin,
    RuntimeModeCommandsMixin,
    RuntimeMutationCommandsMixin,
    MetadataGenerationCommandsMixin,
    MetadataInspectionCommandsMixin,
    ChatFileCommandsMixin,
    MiscCommandsMixin,
):
    """Handles command parsing and execution."""

    def __init__(
        self,
        manager: "SessionManager",
        interaction: Optional[UserInteractionPort] = None,
        helper_ai_invoker: Optional[HelperAIInvoker] = None,
    ) -> None:
        super().__init__(
            manager,
            interaction=interaction,
            helper_ai_invoker=helper_ai_invoker or invoke_helper_ai,
        )
        self._runtime_model_commands = RuntimeModelCommandHandlers(self)
        self._runtime_mode_commands = RuntimeModeCommandHandlers(self)
        self._runtime_mutation_commands = RuntimeMutationCommandHandlers(self)
        self._metadata_generation_commands = MetadataGenerationCommandHandlers(self)
        self._metadata_inspection_commands = MetadataInspectionCommandHandlers(self)
        self._chat_file_commands = ChatFileCommandHandlers(self)
        self._misc_commands = MiscCommandHandlers()
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
