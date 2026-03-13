"""CLI entry point for emojihunt.

Defines two Typer subcommands (catalog, scan), resolves paths, validates
inputs, orchestrates domain logic, and handles top-level errors.
"""

from __future__ import annotations

import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

import typer

from . import __version__
from .analyzer import EmojiAnalyzer
from .errors import EmojihuntError
from .filter import PathFilter
from .models import (
    HandledPath,
    HandledPathStatus,
    ScanContext,
    ScanFinding,
)
from .output_segments import reset_output_segments, start_output_segment
from .path_mapping import map_path
from .reporter import (
    generate_catalog,
    generate_handled_paths_file,
    generate_scan_report,
)
from .scanner import DirectoryScanner

# App root for @ path mapping — the emojihunt package directory
APP_ROOT_ABS = Path(__file__).resolve().parent

app = typer.Typer(
    name="emojihunt",
    help="Scan directories for emoji usage and generate HTML risk reports.",
    add_completion=False,
    no_args_is_help=True,
)


@app.command()
def catalog(
    out_file: Annotated[
        str,
        typer.Option(
            "--out-file",
            help="Path to the output catalog HTML file. Supports ~ and @.",
        ),
    ],
) -> None:
    """Generate a reference HTML catalog of all known emojis."""
    reset_output_segments()

    # Banner
    start_output_segment()
    print(f"emojihunt {__version__}", flush=True)

    try:
        resolved_out = map_path(out_file, app_root_abs=APP_ROOT_ABS)
    except EmojihuntError as exc:
        start_output_segment(file=sys.stderr)
        print(f"ERROR: {exc}", file=sys.stderr)
        raise typer.Exit(1) from None

    # Validate parent directory exists
    if not resolved_out.parent.is_dir():
        start_output_segment(file=sys.stderr)
        print(
            f"ERROR: Output directory does not exist: {resolved_out.parent}",
            file=sys.stderr,
        )
        raise typer.Exit(1)

    start_output_segment()
    print("Generating emoji catalog...")

    analyzer = EmojiAnalyzer()
    emojis = analyzer.get_all_known_emojis()

    generate_catalog(emojis, resolved_out)

    start_output_segment()
    print(f"Catalog written: {resolved_out}")
    print(f"Total emojis:    {len(emojis)}")


@app.command()
def scan(
    target: Annotated[
        list[str],
        typer.Option(
            "--target",
            help="Path to a directory or file to scan. Repeatable. Supports ~ and @.",
        ),
    ],
    report_dir: Annotated[
        str,
        typer.Option(
            "--report-dir",
            help="Directory where report files will be written. Supports ~ and @.",
        ),
    ],
    ignore_file: Annotated[
        str | None,
        typer.Option(
            "--ignore-file",
            help="Path to a file with ignore patterns (one regex per line). Supports ~ and @.",
        ),
    ] = None,
) -> None:
    """Scan target directories/files for emoji usage and generate a report."""
    reset_output_segments()

    # Banner
    start_output_segment()
    print(f"emojihunt {__version__}", flush=True)

    # --- Resolve and validate paths ---
    try:
        resolved_targets = [
            map_path(t, app_root_abs=APP_ROOT_ABS) for t in target
        ]
        resolved_report_dir = map_path(report_dir, app_root_abs=APP_ROOT_ABS)
        resolved_ignore: Path | None = None
        if ignore_file is not None:
            resolved_ignore = map_path(ignore_file, app_root_abs=APP_ROOT_ABS)
    except EmojihuntError as exc:
        start_output_segment(file=sys.stderr)
        print(f"ERROR: {exc}", file=sys.stderr)
        raise typer.Exit(1) from None

    # Validate targets exist
    for t in resolved_targets:
        if not t.exists():
            start_output_segment(file=sys.stderr)
            print(f"ERROR: Target does not exist: {t}", file=sys.stderr)
            raise typer.Exit(1)

    # Validate report directory exists
    if not resolved_report_dir.is_dir():
        start_output_segment(file=sys.stderr)
        print(
            f"ERROR: Report directory does not exist: {resolved_report_dir}",
            file=sys.stderr,
        )
        raise typer.Exit(1)

    # --- Load ignore patterns ---
    if resolved_ignore is not None:
        try:
            path_filter = PathFilter.from_file(resolved_ignore)
        except EmojihuntError as exc:
            start_output_segment(file=sys.stderr)
            print(f"ERROR: {exc}", file=sys.stderr)
            raise typer.Exit(1) from None
    else:
        path_filter = PathFilter.empty()

    # --- Scan ---
    start_output_segment()
    print("Scanning...")
    sys.stdout.flush()

    started = datetime.now(timezone.utc)
    started_local = datetime.now().astimezone()
    wall_start = time.monotonic()

    scanner = DirectoryScanner(resolved_targets, path_filter)
    analyzer = EmojiAnalyzer()

    # Accumulate findings
    emoji_counts: dict[str, tuple[int, ScanFinding]] = {}
    # key = code_points string, value = (count, ScanFinding)
    handled_paths: list[HandledPath] = []
    files_scanned = 0
    files_skipped = 0
    files_errored = 0

    for result in scanner.scan():
        handled_paths.append(result.handled_path)

        if result.handled_path.status == HandledPathStatus.SKIPPED:
            files_skipped += 1
            continue
        if result.handled_path.status == HandledPathStatus.ERROR:
            files_errored += 1
            continue

        files_scanned += 1

        if result.file_content is not None:
            try:
                for line in result.file_content.read_lines():
                    found = analyzer.analyze_line(line)
                    for metadata in found:
                        key = metadata.code_points
                        if key in emoji_counts:
                            count, existing = emoji_counts[key]
                            emoji_counts[key] = (count + 1, existing)
                        else:
                            emoji_counts[key] = (
                                1,
                                ScanFinding(metadata=metadata, occurrence_count=0),
                            )
            except UnicodeDecodeError:
                # File passed initial check but failed during full read
                handled_paths[-1] = HandledPath(
                    result.handled_path.path,
                    HandledPathStatus.SKIPPED,
                )
                files_scanned -= 1
                files_skipped += 1
            except OSError as exc:
                handled_paths[-1] = HandledPath(
                    result.handled_path.path,
                    HandledPathStatus.ERROR,
                    str(exc),
                )
                files_scanned -= 1
                files_errored += 1

    wall_end = time.monotonic()
    finished = datetime.now(timezone.utc)
    finished_local = datetime.now().astimezone()
    duration = wall_end - wall_start

    # Build final findings list
    findings: list[ScanFinding] = []
    total_occurrences = 0
    for count, finding in emoji_counts.values():
        finding.occurrence_count = count
        total_occurrences += count
        findings.append(finding)

    # --- Generate output ---
    timestamp_str = started_local.strftime("%Y-%m-%d_%H-%M-%S")

    report_path = resolved_report_dir / f"{timestamp_str}_emojihunt-report.html"
    paths_path = resolved_report_dir / f"{timestamp_str}_emojihunt-paths.txt"

    context = ScanContext(
        targets=[str(t) for t in resolved_targets],
        ignore_file=str(resolved_ignore) if resolved_ignore else None,
        started_utc=started.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        finished_utc=finished.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        started_local=started_local.strftime("%Y-%m-%d %H:%M:%S"),
        finished_local=finished_local.strftime("%Y-%m-%d %H:%M:%S"),
        duration_seconds=duration,
        files_scanned=files_scanned,
        files_skipped=files_skipped,
        files_errored=files_errored,
        unique_emojis_found=len(findings),
        total_occurrences=total_occurrences,
    )

    generate_scan_report(findings, context, report_path)
    generate_handled_paths_file(handled_paths, paths_path)

    # --- Summary ---
    start_output_segment()
    label_width = 20
    print(f"{'Files scanned:':<{label_width}}{files_scanned}")
    print(f"{'Files skipped:':<{label_width}}{files_skipped}")
    print(f"{'Files errored:':<{label_width}}{files_errored}")
    print(f"{'Unique emojis:':<{label_width}}{len(findings)}")
    print(f"{'Total occurrences:':<{label_width}}{total_occurrences}")
    print(f"{'Duration:':<{label_width}}{duration:.2f}s")

    start_output_segment()
    print(f"Report:  {report_path}")
    print(f"Paths:   {paths_path}")

    if not findings:
        start_output_segment()
        print("No emojis found.")


def main() -> None:
    """Entry point for the emojihunt CLI."""
    try:
        app()
    except KeyboardInterrupt:
        start_output_segment()
        print("Canceled.")
    except EmojihuntError as exc:
        start_output_segment(file=sys.stderr)
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
