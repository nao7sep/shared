"""Command registration metadata and dispatch orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Awaitable, Callable

from ..ai.catalog import PROVIDER_SHORTCUTS
from .types import CommandResult

if TYPE_CHECKING:
    from . import CommandHandler


CommandCallable = Callable[[str], Awaitable[CommandResult]]


@dataclass(frozen=True, slots=True)
class CommandSpec:
    """One command registration entry."""

    name: str
    method_name: str
    aliases: tuple[str, ...] = ()


COMMAND_SPECS: tuple[CommandSpec, ...] = (
    CommandSpec("model", "set_model"),
    CommandSpec("helper", "set_helper"),
    CommandSpec("input", "set_input_mode"),
    CommandSpec("timeout", "set_timeout"),
    CommandSpec("system", "set_system_prompt"),
    CommandSpec("retry", "retry_mode"),
    CommandSpec("apply", "apply_retry"),
    CommandSpec("cancel", "cancel_retry"),
    CommandSpec("secret", "secret_mode_command"),
    CommandSpec("search", "search_mode_command"),
    CommandSpec("rewind", "rewind_messages"),
    CommandSpec("purge", "purge_messages"),
    CommandSpec("history", "show_history"),
    CommandSpec("show", "show_message"),
    CommandSpec("status", "show_status"),
    CommandSpec("title", "set_title"),
    CommandSpec("summary", "set_summary"),
    CommandSpec("safe", "check_safety"),
    CommandSpec("new", "new_chat"),
    CommandSpec("open", "open_chat"),
    CommandSpec("switch", "switch_chat"),
    CommandSpec("close", "close_chat"),
    CommandSpec("rename", "rename_chat_file"),
    CommandSpec("delete", "delete_chat_command"),
    CommandSpec("help", "show_help"),
    CommandSpec("exit", "exit_app", aliases=("quit",)),
)


def build_command_map(handler: "CommandHandler") -> dict[str, CommandCallable]:
    """Build command string to bound async handler map."""
    command_map: dict[str, CommandCallable] = {}

    for spec in COMMAND_SPECS:
        method = getattr(handler, spec.method_name)
        command_map[spec.name] = method
        for alias in spec.aliases:
            command_map[alias] = method

    return command_map


@dataclass(slots=True)
class CommandDispatcher:
    """Resolve and dispatch parsed commands to handler methods."""

    handler: "CommandHandler"
    _command_map: dict[str, CommandCallable] = field(init=False)

    def __post_init__(self) -> None:
        self._command_map = build_command_map(self.handler)

    async def dispatch(self, command: str, args: str) -> CommandResult:
        """Dispatch one command with already-parsed args."""
        if command in PROVIDER_SHORTCUTS:
            return self.handler.switch_provider_shortcut(command)

        command_handler = self._command_map.get(command)
        if command_handler is not None:
            return await command_handler(args)

        raise ValueError(f"Unknown command: /{command}")
