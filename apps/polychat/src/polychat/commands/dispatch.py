"""Command registration metadata and dispatch orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from ..ai.catalog import PROVIDER_SHORTCUTS
from .types import CommandResult


CommandCallable = Callable[[str], Awaitable[CommandResult]]


@dataclass(frozen=True, slots=True)
class CommandSpec:
    """One command registration entry."""

    name: str
    method_name: str
    group: str
    aliases: tuple[str, ...] = ()


COMMAND_SPECS: tuple[CommandSpec, ...] = (
    # Runtime model/timeout
    CommandSpec("model", "set_model", "runtime_model"),
    CommandSpec("helper", "set_helper", "runtime_model"),
    CommandSpec("timeout", "set_timeout", "runtime_model"),
    # Runtime modes
    CommandSpec("input", "set_input_mode", "runtime_mode"),
    CommandSpec("system", "set_system_prompt", "runtime_mode"),
    CommandSpec("retry", "retry_mode", "runtime_mode"),
    CommandSpec("apply", "apply_retry", "runtime_mode"),
    CommandSpec("cancel", "cancel_retry", "runtime_mode"),
    CommandSpec("secret", "secret_mode_command", "runtime_mode"),
    CommandSpec("search", "search_mode_command", "runtime_mode"),
    # Runtime mutation
    CommandSpec("rewind", "rewind_messages", "runtime_mutation"),
    CommandSpec("purge", "purge_messages", "runtime_mutation"),
    # Metadata inspection
    CommandSpec("history", "show_history", "meta_inspection"),
    CommandSpec("show", "show_message", "meta_inspection"),
    CommandSpec("status", "show_status", "meta_inspection"),
    # Metadata generation
    CommandSpec("title", "set_title", "meta_generation"),
    CommandSpec("summary", "set_summary", "meta_generation"),
    CommandSpec("safe", "check_safety", "meta_generation"),
    # Chat files
    CommandSpec("new", "new_chat", "chat_files"),
    CommandSpec("open", "open_chat", "chat_files"),
    CommandSpec("switch", "switch_chat", "chat_files"),
    CommandSpec("close", "close_chat", "chat_files"),
    CommandSpec("rename", "rename_chat_file", "chat_files"),
    CommandSpec("delete", "delete_chat_command", "chat_files"),
    # Misc
    CommandSpec("help", "show_help", "misc"),
    CommandSpec("exit", "exit_app", "misc", aliases=("quit",)),
)


def build_command_map(
    handler_groups: dict[str, Any],
) -> dict[str, CommandCallable]:
    """Build command string → bound async handler map from handler group instances."""
    command_map: dict[str, CommandCallable] = {}

    for spec in COMMAND_SPECS:
        handler = handler_groups[spec.group]
        method = getattr(handler, spec.method_name)
        command_map[spec.name] = method
        for alias in spec.aliases:
            command_map[alias] = method

    return command_map


@dataclass(slots=True)
class CommandDispatcher:
    """Resolve and dispatch parsed commands to handler methods."""

    base_handler: Any
    handler_groups: dict[str, Any]
    _command_map: dict[str, CommandCallable] = field(init=False)

    def __post_init__(self) -> None:
        self._command_map = build_command_map(self.handler_groups)

    async def dispatch(self, command: str, args: str) -> CommandResult:
        """Dispatch one command with already-parsed args."""
        if command in PROVIDER_SHORTCUTS:
            return self.base_handler.switch_provider_shortcut(command)

        command_handler = self._command_map.get(command)
        if command_handler is not None:
            return await command_handler(args)

        raise ValueError(f"Unknown command: /{command}")
