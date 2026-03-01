"""REPL shell loop and interactive session plumbing."""

from __future__ import annotations

import shlex
import sys
from pathlib import Path

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

if sys.platform != "win32":
    import readline  # noqa: F401  # enables line-editing and arrow keys in input()
    readline.set_auto_history(False)


def run_repl(
    db: Database,
    data_path: Path,
    check_path: Path | None,
) -> None:
    """Run the interactive REPL loop until exit/quit."""

    def after_mutation(
        affected_group_ids: set[int] | None,
        removed_check_pages: set[tuple[int, str]] | None,
    ) -> None:
        save_database(db, data_path)
        if check_path is None:
            return
        if removed_check_pages:
            for group_id, group_name in sorted(removed_check_pages):
                remove_check_page(check_path, group_id, group_name)
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
            for msg in exc.lines:
                print(msg)
            continue

        try:
            execute_command(command, db, after_mutation)
        except ViberError as exc:
            print(f"ERROR: {exc}")
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR: Unexpected: {exc}")

