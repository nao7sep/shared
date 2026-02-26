"""REPL shell loop and interactive session plumbing."""

from __future__ import annotations

import shlex
from pathlib import Path
from typing import Any

from .command_parser import CommandParseError, parse_command
from .commands import MutationHook, execute_command
from .errors import ViberError
from .formatter import print_banner, print_segment
from .models import Database
from .renderer import remove_check_page, render_check_pages
from .store import save_database

_BANNER_LINES = (
    "Viber — cross-project maintenance tracker",
    "Type 'help' for commands. Type 'exit' or 'quit' to leave.",
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

    history_path = data_path.with_suffix(f"{data_path.suffix}.history")
    _configure_line_editor(history_path)

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

    try:
        _run_loop(db, after_mutation)
    finally:
        _save_line_editor_history(history_path)


def _run_loop(db: Database, after_mutation: MutationHook) -> None:
    print_banner(_BANNER_LINES)

    while True:
        try:
            raw = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            continue

        line = raw.strip()
        if not line:
            continue
        _record_history_entry(line)

        try:
            tokens = shlex.split(line)
        except ValueError as exc:
            print_segment([f"Parse error: {exc}"])
            continue

        if not tokens:
            continue

        verb = tokens[0].lower()
        verb = _ALIASES.get(verb, verb)

        if verb in ("exit", "quit"):
            print_segment(["Goodbye."], trailing_blank=False)
            break

        try:
            command = parse_command(verb, tokens[1:])
        except CommandParseError as exc:
            print_segment(exc.lines)
            continue

        try:
            execute_command(command, db, after_mutation)
        except ViberError as exc:
            print_segment([f"Error: {exc}"])
        except Exception as exc:  # noqa: BLE001
            print_segment([f"Unexpected error: {exc}"])


def _configure_line_editor(history_path: Path) -> None:
    if readline is None:
        return
    try:
        readline.parse_and_bind("set enable-keypad on")
        readline.parse_and_bind("set editing-mode emacs")
    except Exception:  # noqa: BLE001
        pass
    try:
        if history_path.exists():
            readline.read_history_file(str(history_path))
    except Exception:  # noqa: BLE001
        pass


def _record_history_entry(line: str) -> None:
    if readline is None:
        return
    try:
        last_index = readline.get_current_history_length()
        if last_index > 0 and readline.get_history_item(last_index) == line:
            return
        readline.add_history(line)
    except Exception:  # noqa: BLE001
        return


def _save_line_editor_history(history_path: Path) -> None:
    if readline is None:
        return
    try:
        history_path.parent.mkdir(parents=True, exist_ok=True)
        readline.write_history_file(str(history_path))
    except Exception:  # noqa: BLE001
        return
