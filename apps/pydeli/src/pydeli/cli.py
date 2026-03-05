"""CLI entrypoint: argument parsing, TTY detection, top-level error handling."""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .errors import PydeliError
from .output_segments import reset_segment_state
from .paths import resolve_path, validate_directory
from .ui import banner, error, farewell, fail_fast_not_interactive
from .workflow import run_wizard


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pydeli",
        description="Wizard-style Python release helper for publishing to TestPyPI and PyPI.",
    )
    parser.add_argument(
        "app_dir",
        help="Path to the target app directory containing pyproject.toml.",
    )
    parser.add_argument(
        "--archive-dir",
        required=True,
        help="Path to the archive root directory for storing build artifacts.",
    )
    return parser


def main() -> None:
    reset_segment_state()

    parser = _build_parser()

    # Show help even when required args are missing
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    # Fail on unrecognized options
    args = parser.parse_args()

    # TTY detection — must be interactive
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        fail_fast_not_interactive()

    banner(__version__)

    try:
        app_dir = resolve_path(args.app_dir)
        app_dir = validate_directory(app_dir, "App directory")

        archive_dir = resolve_path(args.archive_dir)
        # archive_dir is created on demand, just validate parent exists
        archive_dir.mkdir(parents=True, exist_ok=True)
        archive_dir = validate_directory(archive_dir, "Archive directory")

        run_wizard(app_dir=app_dir, archive_dir=archive_dir)

    except KeyboardInterrupt:
        print()
        farewell("Canceled.")
    except PydeliError as e:
        error(str(e))
        sys.exit(1)
    except Exception as e:
        error(f"Unexpected error: {e}")
        sys.exit(1)
