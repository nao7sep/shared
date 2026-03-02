"""CLI argument parsing and application startup."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn

from .errors import StartupValidationError, ViberError
from .path_mapping import map_path
from .renderer import render_check_pages
from .repl import run_repl
from .service import prune_orphan_tasks
from .store import load_database, save_database

_USAGE = """\
Usage: viber --data <path> [--check <path>]

Options:
  --data <path>    Path to JSON state file (required).
                   Accepts absolute paths, ~ (home), or @ (app root).
  --check <path>   Optional path for HTML check output files.
                   HTML is regenerated after each mutation.
  --help, -h       Show this help message and exit.

Path examples:
  viber --data ~/viber/data.json
  viber --data ~/viber/data.json --check ~/viber/check.html
"""


@dataclass
class AppArgs:
    data_path: Path
    check_path: Path | None


def parse_args(argv: list[str] | None = None) -> AppArgs | None:
    """Parse CLI arguments. Returns None if --help was requested."""
    args = argv if argv is not None else sys.argv[1:]

    if "--help" in args or "-h" in args:
        print(_USAGE, end="")
        return None

    data_raw: str | None = None
    check_raw: str | None = None

    i = 0
    while i < len(args):
        if args[i] == "--data":
            if i + 1 >= len(args):
                _die("--data requires a path argument.")
            data_raw = args[i + 1]
            i += 2
        elif args[i] == "--check":
            if i + 1 >= len(args):
                _die("--check requires a path argument.")
            check_raw = args[i + 1]
            i += 2
        else:
            _die(f"Unknown argument: {args[i]}")

    if data_raw is None:
        _die("--data is required.")

    data_path = _resolve_path(data_raw, "--data")
    check_path = _resolve_path(check_raw, "--check") if check_raw is not None else None

    return AppArgs(data_path=data_path, check_path=check_path)


def main() -> None:
    """Application entry point."""
    try:
        app_args = parse_args()
    except StartupValidationError as exc:
        _die(str(exc))
    if app_args is None:
        sys.exit(0)

    try:
        db = load_database(app_args.data_path)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: Could not load data file: {exc}", file=sys.stderr)
        sys.exit(1)

    removed_tasks = prune_orphan_tasks(db)
    if removed_tasks:
        try:
            save_database(db, app_args.data_path)
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR: Could not save pruned data file: {exc}", file=sys.stderr)
            sys.exit(1)

    # If --check is configured and we have data, generate initial HTML.
    if app_args.check_path is not None and db.groups:
        try:
            render_check_pages(db, app_args.check_path)
        except Exception as exc:  # noqa: BLE001
            print(f"WARNING: Could not generate HTML check pages: {exc}", file=sys.stderr)

    try:
        run_repl(db, app_args.data_path, app_args.check_path)
    except KeyboardInterrupt:
        print()
        print("Interrupted.")
    except ViberError as exc:
        print(f"ERROR: Fatal: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: Unexpected: {exc}", file=sys.stderr)
        sys.exit(1)


def _resolve_path(raw: str, arg_name: str) -> Path:
    try:
        return map_path(raw, app_root_abs=Path(__file__).resolve().parent)
    except StartupValidationError:
        raise
    except Exception as exc:
        raise StartupValidationError(
            f"{arg_name} path is invalid: {exc}"
        ) from exc


def _die(message: str) -> NoReturn:
    print(f"ERROR: {message}", file=sys.stderr)
    print("Run 'viber --help' for usage.", file=sys.stderr)
    sys.exit(1)
