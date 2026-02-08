"""Command dispatching for tk REPL/CLI."""

from typing import Any

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


def execute_command(cmd: str, args: list[Any], kwargs: dict[str, Any], session: Session) -> str:
    """Execute one parsed command and return user-facing text."""
    cmd = resolve_command_alias(cmd)
    args = _normalize_args(cmd, args)

    if cmd == "init":
        if len(args) != 1:
            raise ValueError("Usage: init <profile_path>")
        result = commands.cmd_init(args[0], session)
        session.clear_last_list()
        return result

    if cmd == "add":
        if len(args) != 1:
            raise ValueError("Usage: add <text...>")
        result = commands.cmd_add(session, args[0])
        session.clear_last_list()
        return result

    if cmd == "list":
        if args or kwargs:
            raise ValueError("Usage: list")
        payload = commands.list_pending_data(session)
        _apply_last_list_mapping_from_payload(session, payload)
        return formatters.format_pending_list(payload)

    if cmd == "history":
        if args:
            raise ValueError("Usage: history [--days N] [--working-days N]")
        payload = commands.list_history_data(
            session,
            days=kwargs.get("days"),
            working_days=kwargs.get("working_days"),
        )
        _apply_last_list_mapping_from_payload(session, payload)
        return formatters.format_history_list(payload)

    if cmd == "done":
        if len(args) != 1:
            raise ValueError("Usage: done <num> [--note <text>] [--date YYYY-MM-DD]")
        result = commands.cmd_done(session, args[0], kwargs.get("note"), kwargs.get("date"))
        session.clear_last_list()
        return result

    if cmd == "cancel":
        if len(args) != 1:
            raise ValueError("Usage: cancel <num> [--note <text>] [--date YYYY-MM-DD]")
        result = commands.cmd_cancel(session, args[0], kwargs.get("note"), kwargs.get("date"))
        session.clear_last_list()
        return result

    if cmd == "edit":
        if len(args) < 2:
            raise ValueError("Usage: edit <num> <text>")
        result = commands.cmd_edit(session, args[0], " ".join(str(a) for a in args[1:]))
        session.clear_last_list()
        return result

    if cmd == "delete":
        if len(args) != 1:
            raise ValueError("Usage: delete <num>")
        result = commands.cmd_delete(session, args[0], confirm=bool(kwargs.get("confirm", False)))
        if result == "Task deleted.":
            session.clear_last_list()
        return result

    if cmd == "note":
        if len(args) < 1:
            raise ValueError("Usage: note <num> [<text>]")
        note_text = " ".join(str(a) for a in args[1:]) if len(args) > 1 else None
        result = commands.cmd_note(session, args[0], note_text)
        session.clear_last_list()
        return result

    if cmd == "date":
        if len(args) != 2:
            raise ValueError("Usage: date <num> <YYYY-MM-DD>")
        result = commands.cmd_date(session, args[0], args[1])
        session.clear_last_list()
        return result

    if cmd == "sync":
        if args or kwargs:
            raise ValueError("Usage: sync")
        result = commands.cmd_sync(session)
        session.clear_last_list()
        return result

    if cmd == "today":
        if args or kwargs:
            raise ValueError("Usage: today")
        payload = commands.cmd_today_data(session)
        _apply_last_list_mapping_from_payload(session, payload)
        return formatters.format_history_list(payload)

    if cmd == "yesterday":
        if args or kwargs:
            raise ValueError("Usage: yesterday")
        payload = commands.cmd_yesterday_data(session)
        _apply_last_list_mapping_from_payload(session, payload)
        return formatters.format_history_list(payload)

    if cmd == "recent":
        if args or kwargs:
            raise ValueError("Usage: recent")
        payload = commands.cmd_recent_data(session)
        _apply_last_list_mapping_from_payload(session, payload)
        return formatters.format_history_list(payload)

    if cmd in ("exit", "quit"):
        return "EXIT"

    raise ValueError(f"Unknown command: {cmd}")
