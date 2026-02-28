"""REPL shell loop and interactive session plumbing."""

from __future__ import annotations

import shlex
from pathlib import Path
from typing import Any

from .command_parser import CommandParseError, parse_command
from .commands import MutationHook, execute_command
from .errors import ViberError
from .models import Database
from .renderer import remove_check_page, render_check_pages
from .store import save_database

def _make_banner() -> str:
    from . import __version__

    return (
        f"viber {__version__}\n"
        "Type 'help' for commands. Type 'exit' or 'quit' to leave."
    )
_ALIASES = {
    "c": "create",
    "r": "read",
    "u": "update",
    "d": "delete",
    "v": "view",
    "o": "ok",
    "n": "nah",
    "w": "work",
    "z": "undo",
}

readline_module: Any
try:
    import readline as readline_module
except ImportError:  # pragma: no cover - platform-dependent
    readline_module = None
readline: Any = readline_module


def run_repl(
    db: Database,
    data_path: Path,
    check_path: Path | None,
) -> None:
    """Run the interactive REPL loop until exit/quit."""
    _configure_line_editor()

    def after_mutation(
        affected_group_ids: set[int] | None,
        removed_group_names: set[str] | None,
    ) -> None:
        save_database(db, data_path)
        if check_path is None:
            return
        if removed_group_names:
            for group_name in sorted(removed_group_names):
                remove_check_page(check_path, group_name)
        if affected_group_ids is None:
            render_check_pages(db, check_path)
            return
        if affected_group_ids:
            render_check_pages(db, check_path, affected_group_ids)

    _run_loop(db, after_mutation)


def _run_loop(db: Database, after_mutation: MutationHook) -> None:
    print(_make_banner())

    while True:
        try:
            print()
            raw = input("> ")
        except EOFError:
            print()
            print("Goodbye.")
            break
        except KeyboardInterrupt:
            print()
            continue

        line = raw.strip()
        if not line:
            continue
        _record_command_history(line)

        try:
            tokens = shlex.split(line)
        except ValueError as exc:
            print(f"ERROR: {exc}")
            continue

        if not tokens:
            continue

        verb = tokens[0].lower()
        verb = _ALIASES.get(verb, verb)

        if verb in ("exit", "quit"):
            print("Goodbye.")
            break

        try:
            command = parse_command(verb, tokens[1:])
        except CommandParseError as exc:
            for line in exc.lines:
                print(line)
            continue

        try:
            execute_command(command, db, after_mutation)
        except ViberError as exc:
            print(f"ERROR: {exc}")
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR: Unexpected: {exc}")


def _configure_line_editor() -> None:
    """Enable basic in-line editing (history stays in-memory only for this session)."""
    if readline is None:
        return
    try:
        # Needed on some terminals so arrow keys work for cursor movement.
        readline.parse_and_bind("set enable-keypad on")
        readline.parse_and_bind("set editing-mode emacs")
        # Only REPL command lines should enter history; confirmations/comments should not.
        set_auto_history = getattr(readline, "set_auto_history", None)
        if callable(set_auto_history):
            set_auto_history(False)
    except Exception:  # noqa: BLE001
        pass


def _record_command_history(line: str) -> None:
    """Record REPL command history explicitly when readline is available."""
    if readline is None:
        return
    add_history = getattr(readline, "add_history", None)
    if not callable(add_history):
        return
    try:
        add_history(line)
    except Exception:  # noqa: BLE001
        pass
