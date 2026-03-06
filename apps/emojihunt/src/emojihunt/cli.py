"""CLI argument parsing and command dispatch."""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from .catalog_html import generate_catalog_html
from .emoji_data import load_emoji_dataset
from .errors import EmojihuntError
from .models import RiskLevel
from .output_segments import start_segment
from .path_mapping import map_user_path
from .report_html import generate_report_html
from .scanner import scan_targets


def run_cli(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="emojihunt",
        description="Scan files for emoji usage and produce HTML artifacts for review.",
    )
    subparsers = parser.add_subparsers(dest="command")

    catalog_parser = subparsers.add_parser(
        "catalog",
        help="Generate the full emoji catalog as HTML.",
    )
    catalog_parser.add_argument(
        "--output",
        required=True,
        help="Output file path for the catalog HTML.",
    )

    scan_parser = subparsers.add_parser(
        "scan",
        help="Scan targets for emoji and generate a findings report.",
    )
    scan_parser.add_argument(
        "--target",
        action="append",
        required=True,
        dest="targets",
        help="File or directory to scan (can be repeated).",
    )
    scan_parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory for the generated findings report.",
    )
    scan_parser.add_argument(
        "--ignore-file",
        default=None,
        help="File containing ignore patterns (gitignore syntax).",
    )

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    if args.command == "catalog":
        _run_catalog(args)
    elif args.command == "scan":
        _run_scan(args)


def _run_catalog(args: argparse.Namespace) -> None:
    output_path = map_user_path(args.output)

    start_segment()
    print("Loading emoji dataset...")
    dataset = load_emoji_dataset(fully_qualified_only=True)
    entries = list(dataset.values())

    start_segment()
    print(f"Generating catalog with {len(entries)} emoji sequences...")

    html_content = generate_catalog_html(entries)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_content, encoding="utf-8")

    start_segment()
    print(f"Catalog written to {output_path}")


def _run_scan(args: argparse.Namespace) -> None:
    targets = [map_user_path(t) for t in args.targets]
    output_dir = map_user_path(args.output_dir)
    ignore_file = map_user_path(args.ignore_file) if args.ignore_file else None

    for target in targets:
        if not target.exists():
            raise EmojihuntError(f"Scan target does not exist: {target}")

    if not output_dir.is_dir():
        output_dir.mkdir(parents=True, exist_ok=True)

    start_segment()
    print("Loading emoji dataset...")
    dataset = load_emoji_dataset()

    start_segment()
    target_list = "\n".join(f"  {t}" for t in targets)
    print(f"Scanning {len(targets)} target(s):\n{target_list}")

    result = scan_targets(targets, ignore_file, dataset)

    if result.warnings:
        start_segment()
        for warning in result.warnings:
            print(f"WARNING: {warning}")

    if not result.findings:
        start_segment()
        print("No emoji findings.")
        return

    now_local = datetime.now()
    now_utc = datetime.now(timezone.utc)

    html_content = generate_report_html(
        result.findings,
        generated_at_local=now_local,
        generated_at_utc=now_utc,
    )

    filename = now_local.strftime("%Y-%m-%d_%H-%M-%S_emoji-findings.html")
    output_path = output_dir / filename
    output_path.write_text(html_content, encoding="utf-8")

    paths_filename = now_local.strftime("%Y-%m-%d_%H-%M-%S_scanned-paths.txt")
    paths_output = output_dir / paths_filename
    paths_output.write_text(
        "\n".join(str(p) for p in sorted(result.scanned_files)) + "\n",
        encoding="utf-8",
    )

    _print_summary(result.findings, output_path, paths_output)


def _print_summary(findings: list, output_path: Path, paths_output: Path) -> None:
    red_count = sum(1 for f in findings if f.entry.risk_level == RiskLevel.RED)
    yellow_count = sum(1 for f in findings if f.entry.risk_level == RiskLevel.YELLOW)
    none_count = sum(1 for f in findings if f.entry.risk_level == RiskLevel.NONE)
    total_occurrences = sum(f.count for f in findings)

    summary = [
        ("Unique sequences", str(len(findings))),
        ("Total occurrences", str(total_occurrences)),
        ("Red", str(red_count)),
        ("Yellow", str(yellow_count)),
        ("No risk", str(none_count)),
    ]
    col = max(len(k) for k, _ in summary) + 2

    start_segment()
    for key, value in summary:
        label = f"{key}:"
        print(f"{label:<{col}} {value}")

    start_segment()
    print(f"Report written to    {output_path}")
    print(f"Scanned paths log to {paths_output}")
