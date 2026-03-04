"""CLI entry and startup wiring."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .errors import RevzipError
from .ignore_rules import load_ignore_rule_set
from .output_segments import reset_output_segments, start_output_segment
from .path_mapping import resolve_startup_paths
from .presenters import render_error
from .repl import run_repl


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    reset_output_segments()

    app_root_abs = Path(__file__).resolve().parent

    try:
        resolved_paths = resolve_startup_paths(
            source_arg_raw=args.source,
            dest_arg_raw=args.dest,
            ignore_arg_raw=args.ignore,
            app_root_abs=app_root_abs,
        )
        ignore_rule_set = load_ignore_rule_set(resolved_paths.ignore_file_abs)
        return run_repl(
            resolved_paths=resolved_paths,
            ignore_rule_set=ignore_rule_set,
        )
    except KeyboardInterrupt:
        print()
        print("Canceled.")
        return 0
    except RevzipError as exc:
        start_output_segment()
        print(render_error(str(exc)))
        return 1
    except Exception as exc:
        start_output_segment(file=sys.stderr)
        print(render_error(str(exc)), file=sys.stderr)
        return 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="revzip",
        description="Archive and restore directory snapshots.",
    )
    parser.add_argument(
        "--source",
        required=True,
        help="Absolute source directory path (or path mapped with ~ / @).",
    )
    parser.add_argument(
        "--dest",
        required=True,
        help="Absolute destination directory path (or path mapped with ~ / @).",
    )
    parser.add_argument(
        "--ignore",
        required=False,
        help="Optional path to ignore regex file (absolute or mapped with ~ / @).",
    )
    return parser
