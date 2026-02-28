"""Command system façade for PolyChat."""

from typing import Any, Optional, TYPE_CHECKING

from ..chat import save_chat
from ..ai.helper_runtime import invoke_helper_ai
from .base import CommandHandlerBaseMixin
from .context import HelperAIInvoker
from .dispatch import CommandDispatcher
from .runtime_models import RuntimeModelCommandHandlers
from .runtime_modes import RuntimeModeCommandHandlers
from .runtime_mutation import RuntimeMutationCommandHandlers
from .meta_generation import MetadataGenerationCommandHandlers
from .meta_inspection import MetadataInspectionCommandHandlers
from .chat_files import ChatFileCommandHandlers
from .misc import MiscCommandHandlers
from .types import CommandResult
from ..ui.interaction import UserInteractionPort

if TYPE_CHECKING:
    from ..session_manager import SessionManager


class CommandHandler(CommandHandlerBaseMixin):
    """Handles command parsing and execution.

    Individual command groups are composed as handler instances, not mixins.
    Methods are resolved via ``__getattr__`` delegation for direct access
    and via ``CommandDispatcher`` for ``/command`` dispatch.
    """

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
        self._handler_groups: dict[str, Any] = {
            "runtime_model": RuntimeModelCommandHandlers(self),
            "runtime_mode": RuntimeModeCommandHandlers(self),
            "runtime_mutation": RuntimeMutationCommandHandlers(self),
            "meta_generation": MetadataGenerationCommandHandlers(self),
            "meta_inspection": MetadataInspectionCommandHandlers(self),
            "chat_files": ChatFileCommandHandlers(self),
            "misc": MiscCommandHandlers(),
        }
        self._dispatcher = CommandDispatcher(self, self._handler_groups)

    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to handler group instances.

        This replaces the mixin inheritance pattern: instead of
        ``CommandHandler`` inheriting forwarding stubs from 7 mixins,
        it resolves methods on the handler instances at access time.
        """
        for handler in self._handler_groups.values():
            method = getattr(handler, name, None)
            if method is not None:
                return method
        raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")

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
