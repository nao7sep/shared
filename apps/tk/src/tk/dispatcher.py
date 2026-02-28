"""Command dispatching for tk REPL/CLI."""

from dataclasses import dataclass
from typing import Any, Callable

from tk import commands, formatters
from tk.errors import TkUsageError
from tk.models import HistoryListPayload, PendingListPayload
from tk.session import Session

COMMAND_ALIASES = {
    "a": "add",
    "l": "list",
    "h": "history",
    "d": "done",
    "c": "cancel",
    "e": "edit",
    "n": "note",
    "s": "sync",
    "t": "today",
    "y": "yesterday",
    "r": "recent",
}
_INT_FIRST_ARG_COMMANDS = frozenset(
    ("edit", "done", "cancel", "delete", "note", "date")
)
_HELP_COMMAND_GROUPS = (
    ("add", "list", "help", "done", "cancel", "edit", "note", "delete"),
    ("history", "today", "yesterday", "recent"),
    ("date", "sync"),
)


@dataclass
class CommandHandler:
    """Defines how to execute a command."""

    executor: Callable[[list[Any], dict[str, Any], Session], str]
    clears_list: bool = True
    usage: str = ""
    summary: str = ""


def resolve_command_alias(cmd: str) -> str:
    """Expand shortcut command to full command name."""
    return COMMAND_ALIASES.get(cmd, cmd)


def _normalize_args(cmd: str, args: list[Any]) -> list[Any]:
    """Normalize raw positional arguments for dispatch."""
    normalized = list(args)

    if cmd == "add" and normalized:
        return [" ".join(str(a) for a in normalized)]

    if cmd in _INT_FIRST_ARG_COMMANDS and normalized:
        try:
            normalized[0] = int(normalized[0])
        except ValueError:
            pass

    return normalized


def _apply_last_list_mapping_from_payload(
    session: Session,
    payload: PendingListPayload | HistoryListPayload,
) -> None:
    """Update session mapping based on payload rows shown to user."""
    session.set_last_list(commands.extract_last_list_mapping(payload))


def _exec_add(args: list[Any], kwargs: dict[str, Any], session: Session) -> str:
    if len(args) != 1:
        raise TkUsageError("Usage: add <text...>")
    return commands.cmd_add(session, args[0])


def _exec_list(args: list[Any], kwargs: dict[str, Any], session: Session) -> str:
    if args or kwargs:
        raise TkUsageError("Usage: list")
    payload = commands.list_pending_data(session)
    _apply_last_list_mapping_from_payload(session, payload)
    return formatters.format_pending_list(payload)


def _exec_history(args: list[Any], kwargs: dict[str, Any], session: Session) -> str:
    if args:
        raise TkUsageError("Usage: history [--days N] [--working-days N]")
    payload = commands.list_history_data(
        session,
        days=kwargs.get("days"),
        working_days=kwargs.get("working_days"),
    )
    _apply_last_list_mapping_from_payload(session, payload)
    return formatters.format_history_list(payload)


def _exec_done(args: list[Any], kwargs: dict[str, Any], session: Session) -> str:
    if len(args) != 1 or not isinstance(args[0], int):
        raise TkUsageError("Usage: done <num>")
    array_index = session.resolve_array_index(args[0])
    return commands.cmd_done(session, array_index, kwargs.get("note"), kwargs.get("date"))


def _exec_cancel(args: list[Any], kwargs: dict[str, Any], session: Session) -> str:
    if len(args) != 1 or not isinstance(args[0], int):
        raise TkUsageError("Usage: cancel <num>")
    array_index = session.resolve_array_index(args[0])
    return commands.cmd_cancel(session, array_index, kwargs.get("note"), kwargs.get("date"))


def _exec_edit(args: list[Any], kwargs: dict[str, Any], session: Session) -> str:
    if len(args) < 2:
        raise TkUsageError("Usage: edit <num> <text>")
    array_index = session.resolve_array_index(args[0])
    return commands.cmd_edit(session, array_index, " ".join(str(a) for a in args[1:]))


def _exec_delete(args: list[Any], kwargs: dict[str, Any], session: Session) -> str:
    if len(args) != 1:
        raise TkUsageError("Usage: delete <num>")
    array_index = session.resolve_array_index(args[0])
    return commands.cmd_delete(session, array_index, confirm=bool(kwargs.get("confirm", False)))


def _exec_note(args: list[Any], kwargs: dict[str, Any], session: Session) -> str:
    if len(args) < 1:
        raise TkUsageError("Usage: note <num> [<text>]")
    array_index = session.resolve_array_index(args[0])
    note_text = " ".join(str(a) for a in args[1:]) if len(args) > 1 else None
    return commands.cmd_note(session, array_index, note_text)


def _exec_date(args: list[Any], kwargs: dict[str, Any], session: Session) -> str:
    if len(args) != 2:
        raise TkUsageError("Usage: date <num> <YYYY-MM-DD>")
    array_index = session.resolve_array_index(args[0])
    return commands.cmd_date(session, array_index, args[1])


def _exec_sync(args: list[Any], kwargs: dict[str, Any], session: Session) -> str:
    if args or kwargs:
        raise TkUsageError("Usage: sync")
    return commands.cmd_sync(session)


def _exec_today(args: list[Any], kwargs: dict[str, Any], session: Session) -> str:
    if args or kwargs:
        raise TkUsageError("Usage: today")
    payload = commands.cmd_today_data(session)
    _apply_last_list_mapping_from_payload(session, payload)
    return formatters.format_history_list(payload)


def _exec_yesterday(args: list[Any], kwargs: dict[str, Any], session: Session) -> str:
    if args or kwargs:
        raise TkUsageError("Usage: yesterday")
    payload = commands.cmd_yesterday_data(session)
    _apply_last_list_mapping_from_payload(session, payload)
    return formatters.format_history_list(payload)


def _exec_recent(args: list[Any], kwargs: dict[str, Any], session: Session) -> str:
    if args or kwargs:
        raise TkUsageError("Usage: recent")
    payload = commands.cmd_recent_data(session)
    _apply_last_list_mapping_from_payload(session, payload)
    return formatters.format_history_list(payload)


def _exec_help(args: list[Any], kwargs: dict[str, Any], session: Session) -> str:
    if args or kwargs:
        raise TkUsageError("Usage: help")
    return render_help_text()


def _alias_for_command(command: str) -> str | None:
    """Return shortcut alias for a command if one exists."""
    for alias, full in COMMAND_ALIASES.items():
        if full == command:
            return alias
    return None


def _display_usage(command: str, usage: str) -> str:
    """Attach alias to usage text for help display."""
    alias = _alias_for_command(command)
    if not alias:
        return usage

    if usage.startswith(command):
        return f"{command} ({alias}){usage[len(command):]}"
    return f"{usage} ({alias})"


def command_doc_entries() -> list[dict[str, str]]:
    """Return command metadata used for help and doc checks."""
    entries: list[dict[str, str]] = []
    for command, handler in COMMAND_REGISTRY.items():
        entries.append(
            {
                "command": command,
                "alias": _alias_for_command(command) or "",
                "usage": handler.usage,
                "summary": handler.summary,
                "display_usage": _display_usage(command, handler.usage),
            }
        )

    entries.append(
        {
            "command": "exit",
            "alias": "quit",
            "usage": "exit / quit",
            "summary": "Exit (Ctrl-D also works)",
            "display_usage": "exit / quit",
        }
    )
    return entries


def render_help_text() -> str:
    """Render help text directly from command registry metadata."""
    entries_by_command = {entry["command"]: entry for entry in command_doc_entries()}
    rows = [entries_by_command[cmd] for group in _HELP_COMMAND_GROUPS for cmd in group]
    rows.append(entries_by_command["exit"])
    width = max(len(row["display_usage"]) for row in rows)

    lines = ["Available commands:"]
    for group in _HELP_COMMAND_GROUPS:
        for command in group:
            entry = entries_by_command[command]
            lines.append(
                f"  {entry['display_usage'].ljust(width)} - {entry['summary']}"
            )
        lines.append("")

    exit_entry = entries_by_command["exit"]
    lines.append(
        f"  {exit_entry['display_usage'].ljust(width)} - {exit_entry['summary']}"
    )
    lines.append("")
    lines.append("Run 'list', 'history', 'today', 'yesterday', or 'recent' first to get task numbers.")
    lines.append("For full documentation, see README.md")
    return "\n".join(lines)


# Command registry
COMMAND_REGISTRY = {
    "add": CommandHandler(_exec_add, clears_list=True, usage="add <text>", summary="Add a task"),
    "list": CommandHandler(_exec_list, clears_list=False, usage="list", summary="Show pending tasks"),
    "history": CommandHandler(
        _exec_history,
        clears_list=False,
        usage="history [--days N] [--working-days N]",
        summary="Show completed/cancelled tasks",
    ),
    "done": CommandHandler(_exec_done, clears_list=True, usage="done <num>", summary="Mark as done (with interactive prompts)"),
    "cancel": CommandHandler(_exec_cancel, clears_list=True, usage="cancel <num>", summary="Mark as cancelled"),
    "edit": CommandHandler(_exec_edit, clears_list=True, usage="edit <num> <text>", summary="Change task text"),
    "delete": CommandHandler(_exec_delete, clears_list=True, usage="delete <num>", summary="Permanently delete task (requires confirmation)"),
    "note": CommandHandler(_exec_note, clears_list=True, usage="note <num> [<text>]", summary="Add/update/remove note"),
    "date": CommandHandler(_exec_date, clears_list=True, usage="date <num> <YYYY-MM-DD>", summary="Change subjective date (handled tasks only)"),
    "sync": CommandHandler(_exec_sync, clears_list=True, usage="sync", summary="Regenerate TODO.md manually"),
    "today": CommandHandler(_exec_today, clears_list=False, usage="today", summary="Show today's handled tasks"),
    "yesterday": CommandHandler(_exec_yesterday, clears_list=False, usage="yesterday", summary="Show yesterday's handled tasks"),
    "recent": CommandHandler(_exec_recent, clears_list=False, usage="recent", summary="Show last 3 working days"),
    "help": CommandHandler(_exec_help, clears_list=False, usage="help", summary="Show available commands"),
}


def execute_command(cmd: str, args: list[Any], kwargs: dict[str, Any], session: Session) -> str:
    """Execute one parsed command and return user-facing text."""
    cmd = resolve_command_alias(cmd)
    args = _normalize_args(cmd, args)

    # Handle special exit commands
    if cmd in ("exit", "quit"):
        return "EXIT"

    # Look up command in registry
    handler = COMMAND_REGISTRY.get(cmd)
    if not handler:
        raise TkUsageError(f"Unknown command: {cmd}")

    # Execute command
    result = handler.executor(args, kwargs, session)

    # Clear list mapping if needed
    if handler.clears_list:
        session.clear_last_list()

    return result
