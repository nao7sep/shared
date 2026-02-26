"""CLI argument parsing and application startup."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn

from .constants import (
    ARG_CHECK,
    ARG_DATA,
    ARG_HELP_LONG,
    ARG_HELP_SHORT,
    CLI_HELP_HINT,
    CLI_USAGE,
    STDERR_ERROR_PREFIX,
    STDERR_FATAL_PREFIX,
    STDERR_HTML_WARN_PREFIX,
    STDERR_LOAD_ERROR_PREFIX,
)
from .errors import StartupValidationError, ViberError
from .path_mapping import map_path
from .renderer import render_check_pages
from .repl import run_repl
from .store import load_database

_APP_ROOT = Path(__file__).parent


@dataclass
class AppArgs:
    data_path: Path
    check_path: Path | None


def parse_args(argv: list[str] | None = None) -> AppArgs | None:
    """Parse CLI arguments. Returns None if --help was requested."""
    args = argv if argv is not None else sys.argv[1:]

    if ARG_HELP_LONG in args or ARG_HELP_SHORT in args:
        print(CLI_USAGE, end="")
        return None

    data_raw: str | None = None
    check_raw: str | None = None

    i = 0
    while i < len(args):
        if args[i] == ARG_DATA:
            if i + 1 >= len(args):
                _die(f"{ARG_DATA} requires a path argument.")
            data_raw = args[i + 1]
            i += 2
        elif args[i] == ARG_CHECK:
            if i + 1 >= len(args):
                _die(f"{ARG_CHECK} requires a path argument.")
            check_raw = args[i + 1]
            i += 2
        else:
            _die(f"Unknown argument: {args[i]}")

    if data_raw is None:
        _die(f"{ARG_DATA} is required.")

    data_path = _resolve_path(data_raw, ARG_DATA)
    check_path = _resolve_path(check_raw, ARG_CHECK) if check_raw is not None else None

    return AppArgs(data_path=data_path, check_path=check_path)


def main() -> None:
    """Application entry point."""
    app_args = parse_args()
    if app_args is None:
        sys.exit(0)

    try:
        db = load_database(app_args.data_path)
    except Exception as exc:  # noqa: BLE001
        print(f"{STDERR_LOAD_ERROR_PREFIX}{exc}", file=sys.stderr)
        sys.exit(1)

    # If --check is configured and we have data, generate initial HTML.
    if app_args.check_path is not None and db.groups:
        try:
            render_check_pages(db, app_args.check_path)
        except Exception as exc:  # noqa: BLE001
            print(f"{STDERR_HTML_WARN_PREFIX}{exc}", file=sys.stderr)

    try:
        run_repl(db, app_args.data_path, app_args.check_path)
    except ViberError as exc:
        print(f"{STDERR_FATAL_PREFIX}{exc}", file=sys.stderr)
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
    print(f"{STDERR_ERROR_PREFIX}{message}", file=sys.stderr)
    print(CLI_HELP_HINT, file=sys.stderr)
    sys.exit(1)
