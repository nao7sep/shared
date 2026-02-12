"""Command dispatching for tk REPL/CLI."""

from dataclasses import dataclass
from typing import Any, Callable

from tk import commands, formatters
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


@dataclass
class CommandHandler:
    """Defines how to execute a command."""
    executor: Callable[[list[Any], dict[str, Any], Session], str]
    clears_list: bool = True
    usage: str = ""


def resolve_command_alias(cmd: str) -> str:
    """Expand shortcut command to full command name."""
    return COMMAND_ALIASES.get(cmd, cmd)


def _normalize_args(cmd: str, args: list[Any]) -> list[Any]:
    """Normalize raw positional arguments for dispatch."""
    normalized = list(args)

    if cmd == "add" and normalized:
        return [" ".join(str(a) for a in normalized)]

    if cmd in ("edit", "done", "cancel", "delete", "note", "date") and normalized:
        try:
            normalized[0] = int(normalized[0])
        except ValueError:
            pass

    return normalized


def _apply_last_list_mapping_from_payload(session: Session, payload: dict[str, Any]) -> None:
    """Update session mapping based on payload rows shown to user."""
    session.set_last_list(commands.extract_last_list_mapping(payload))


# Command executor functions
def _exec_init(args: list[Any], kwargs: dict[str, Any], session: Session) -> str:
    if len(args) != 1:
        raise ValueError("Usage: init <profile_path>")
    return commands.cmd_init(args[0], session)


def _exec_add(args: list[Any], kwargs: dict[str, Any], session: Session) -> str:
    if len(args) != 1:
        raise ValueError("Usage: add <text...>")
    return commands.cmd_add(session, args[0])


def _exec_list(args: list[Any], kwargs: dict[str, Any], session: Session) -> str:
    if args or kwargs:
        raise ValueError("Usage: list")
    payload = commands.list_pending_data(session)
    _apply_last_list_mapping_from_payload(session, payload)
    return formatters.format_pending_list(payload)


def _exec_history(args: list[Any], kwargs: dict[str, Any], session: Session) -> str:
    if args:
        raise ValueError("Usage: history [--days N] [--working-days N]")
    payload = commands.list_history_data(
        session,
        days=kwargs.get("days"),
        working_days=kwargs.get("working_days"),
    )
    _apply_last_list_mapping_from_payload(session, payload)
    return formatters.format_history_list(payload)


def _exec_done(args: list[Any], kwargs: dict[str, Any], session: Session) -> str:
    if len(args) != 1:
        raise ValueError("Usage: done <num> [--note <text>] [--date YYYY-MM-DD]")
    array_index = session.resolve_array_index(args[0])
    return commands.cmd_done(session, array_index, kwargs.get("note"), kwargs.get("date"))


def _exec_cancel(args: list[Any], kwargs: dict[str, Any], session: Session) -> str:
    if len(args) != 1:
        raise ValueError("Usage: cancel <num> [--note <text>] [--date YYYY-MM-DD]")
    array_index = session.resolve_array_index(args[0])
    return commands.cmd_cancel(session, array_index, kwargs.get("note"), kwargs.get("date"))


def _exec_edit(args: list[Any], kwargs: dict[str, Any], session: Session) -> str:
    if len(args) < 2:
        raise ValueError("Usage: edit <num> <text>")
    array_index = session.resolve_array_index(args[0])
    return commands.cmd_edit(session, array_index, " ".join(str(a) for a in args[1:]))


def _exec_delete(args: list[Any], kwargs: dict[str, Any], session: Session) -> str:
    if len(args) != 1:
        raise ValueError("Usage: delete <num>")
    array_index = session.resolve_array_index(args[0])
    return commands.cmd_delete(session, array_index, confirm=bool(kwargs.get("confirm", False)))


def _exec_note(args: list[Any], kwargs: dict[str, Any], session: Session) -> str:
    if len(args) < 1:
        raise ValueError("Usage: note <num> [<text>]")
    array_index = session.resolve_array_index(args[0])
    note_text = " ".join(str(a) for a in args[1:]) if len(args) > 1 else None
    return commands.cmd_note(session, array_index, note_text)


def _exec_date(args: list[Any], kwargs: dict[str, Any], session: Session) -> str:
    if len(args) != 2:
        raise ValueError("Usage: date <num> <YYYY-MM-DD>")
    array_index = session.resolve_array_index(args[0])
    return commands.cmd_date(session, array_index, args[1])


def _exec_sync(args: list[Any], kwargs: dict[str, Any], session: Session) -> str:
    if args or kwargs:
        raise ValueError("Usage: sync")
    return commands.cmd_sync(session)


def _exec_today(args: list[Any], kwargs: dict[str, Any], session: Session) -> str:
    if args or kwargs:
        raise ValueError("Usage: today")
    payload = commands.cmd_today_data(session)
    _apply_last_list_mapping_from_payload(session, payload)
    return formatters.format_history_list(payload)


def _exec_yesterday(args: list[Any], kwargs: dict[str, Any], session: Session) -> str:
    if args or kwargs:
        raise ValueError("Usage: yesterday")
    payload = commands.cmd_yesterday_data(session)
    _apply_last_list_mapping_from_payload(session, payload)
    return formatters.format_history_list(payload)


def _exec_recent(args: list[Any], kwargs: dict[str, Any], session: Session) -> str:
    if args or kwargs:
        raise ValueError("Usage: recent")
    payload = commands.cmd_recent_data(session)
    _apply_last_list_mapping_from_payload(session, payload)
    return formatters.format_history_list(payload)


def _exec_help(args: list[Any], kwargs: dict[str, Any], session: Session) -> str:
    if args or kwargs:
        raise ValueError("Usage: help")
    return """Available commands:

  add (a) <text>          - Add a task
  list (l)                - Show pending tasks
  done (d) <num>          - Mark task as done (interactive)
  cancel (c) <num>        - Mark task as cancelled (interactive)
  edit (e) <num> <text>   - Change task text
  note (n) <num> [<text>] - Add/update/remove note
  delete <num>            - Delete task permanently

  history (h) [--days N] [--working-days N]
  today (t)               - Today's completed tasks
  yesterday (y)           - Yesterday's completed tasks
  recent (r)              - Last 3 working days

  date <num> <YYYY-MM-DD> - Change subjective date
  sync (s)                - Regenerate TODO.md
  exit / quit             - Exit (Ctrl-D also works)

Run 'list' or 'history' first to get task numbers.
For full documentation, see README.md"""


# Command registry
COMMAND_REGISTRY = {
    "init": CommandHandler(_exec_init, clears_list=True, usage="init <profile_path>"),
    "add": CommandHandler(_exec_add, clears_list=True, usage="add <text...>"),
    "list": CommandHandler(_exec_list, clears_list=False, usage="list"),
    "history": CommandHandler(_exec_history, clears_list=False, usage="history [--days N] [--working-days N]"),
    "done": CommandHandler(_exec_done, clears_list=True, usage="done <num> [--note <text>] [--date YYYY-MM-DD]"),
    "cancel": CommandHandler(_exec_cancel, clears_list=True, usage="cancel <num> [--note <text>] [--date YYYY-MM-DD]"),
    "edit": CommandHandler(_exec_edit, clears_list=True, usage="edit <num> <text>"),
    "delete": CommandHandler(_exec_delete, clears_list=True, usage="delete <num>"),
    "note": CommandHandler(_exec_note, clears_list=True, usage="note <num> [<text>]"),
    "date": CommandHandler(_exec_date, clears_list=True, usage="date <num> <YYYY-MM-DD>"),
    "sync": CommandHandler(_exec_sync, clears_list=True, usage="sync"),
    "today": CommandHandler(_exec_today, clears_list=False, usage="today"),
    "yesterday": CommandHandler(_exec_yesterday, clears_list=False, usage="yesterday"),
    "recent": CommandHandler(_exec_recent, clears_list=False, usage="recent"),
    "help": CommandHandler(_exec_help, clears_list=False, usage="help"),
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
        raise ValueError(f"Unknown command: {cmd}")

    # Execute command
    result = handler.executor(args, kwargs, session)

    # Clear list mapping if needed
    if handler.clears_list:
        session.clear_last_list()

    return result
