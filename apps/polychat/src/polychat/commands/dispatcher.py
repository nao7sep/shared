"""Command dispatch orchestration (shortcuts + registry lookup)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .. import models
from .registry import CommandCallable, build_command_map
from .types import CommandResult

if TYPE_CHECKING:
    from . import CommandHandler


@dataclass(slots=True)
class CommandDispatcher:
    """Resolve and dispatch parsed commands to handler methods."""

    handler: "CommandHandler"
    _command_map: dict[str, CommandCallable] = field(init=False)

    def __post_init__(self) -> None:
        self._command_map = build_command_map(self.handler)

    async def dispatch(self, command: str, args: str) -> CommandResult:
        """Dispatch one command with already-parsed args."""
        if command in models.PROVIDER_SHORTCUTS:
            return self.handler.switch_provider_shortcut(command)

        command_handler = self._command_map.get(command)
        if command_handler is not None:
            return await command_handler(args)

        raise ValueError(f"Unknown command: /{command}")
