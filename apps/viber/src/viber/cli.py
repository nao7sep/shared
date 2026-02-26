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
from .store import load_database

_APP_ROOT = Path(__file__).parent
_ARG_HELP_LONG = "--help"
_ARG_HELP_SHORT = "-h"
_ARG_DATA = "--data"
_ARG_CHECK = "--check"

_USAGE = """\
Usage: viber --data <path> [--check <path>]

Options:
  --data <path>    Path to JSON state file (required).
                   Accepts absolute paths, ~ (home), or @ (app root).
  --check <path>   Optional path for HTML check output files.
                   HTML is regenerated after each mutation.
  --help           Show this help message and exit.

Path examples:
  viber --data ~/viber/data.json
  viber --data ~/viber/data.json --check ~/viber/check.html
"""
_HELP_HINT = "Run 'viber --help' for usage."
_STDERR_LOAD_ERROR_PREFIX = "Error loading data file: "
_STDERR_HTML_WARN_PREFIX = "Warning: Could not generate HTML check pages: "
_STDERR_FATAL_PREFIX = "Fatal error: "
_STDERR_ERROR_PREFIX = "Error: "


@dataclass
class AppArgs:
    data_path: Path
    check_path: Path | None


def parse_args(argv: list[str] | None = None) -> AppArgs | None:
    """Parse CLI arguments. Returns None if --help was requested."""
    args = argv if argv is not None else sys.argv[1:]

    if _ARG_HELP_LONG in args or _ARG_HELP_SHORT in args:
        print(_USAGE, end="")
        return None

    data_raw: str | None = None
    check_raw: str | None = None

    i = 0
    while i < len(args):
        if args[i] == _ARG_DATA:
            if i + 1 >= len(args):
                _die(f"{_ARG_DATA} requires a path argument.")
            data_raw = args[i + 1]
            i += 2
        elif args[i] == _ARG_CHECK:
            if i + 1 >= len(args):
                _die(f"{_ARG_CHECK} requires a path argument.")
            check_raw = args[i + 1]
            i += 2
        else:
            _die(f"Unknown argument: {args[i]}")

    if data_raw is None:
        _die(f"{_ARG_DATA} is required.")

    data_path = _resolve_path(data_raw, _ARG_DATA)
    check_path = _resolve_path(check_raw, _ARG_CHECK) if check_raw is not None else None

    return AppArgs(data_path=data_path, check_path=check_path)


def main() -> None:
    """Application entry point."""
    app_args = parse_args()
    if app_args is None:
        sys.exit(0)

    try:
        db = load_database(app_args.data_path)
    except Exception as exc:  # noqa: BLE001
        print(f"{_STDERR_LOAD_ERROR_PREFIX}{exc}", file=sys.stderr)
        sys.exit(1)

    # If --check is configured and we have data, generate initial HTML.
    if app_args.check_path is not None and db.groups:
        try:
            render_check_pages(db, app_args.check_path)
        except Exception as exc:  # noqa: BLE001
            print(f"{_STDERR_HTML_WARN_PREFIX}{exc}", file=sys.stderr)

    try:
        run_repl(db, app_args.data_path, app_args.check_path)
    except ViberError as exc:
        print(f"{_STDERR_FATAL_PREFIX}{exc}", file=sys.stderr)
        sys.exit(1)


def _resolve_path(raw: str, arg_name: str) -> Path:
    try:
        return map_path(raw, app_root_abs=_APP_ROOT)
    except StartupValidationError:
        raise
    except Exception as exc:
        raise StartupValidationError(
            f"{arg_name} path is invalid: {exc}"
        ) from exc


def _die(message: str) -> NoReturn:
    print(f"{_STDERR_ERROR_PREFIX}{message}", file=sys.stderr)
    print(_HELP_HINT, file=sys.stderr)
    sys.exit(1)
