"""Interactive menu loop."""

from __future__ import annotations

from .archive_service import create_snapshot
from .errors import RevzipError
from .extract_service import restore_snapshot
from .models import IgnoreRuleSet, ResolvedPaths, SnapshotRecord
from .presenters import (
    render_app_banner,
    render_error,
    render_loaded_parameters,
    render_main_menu,
    render_snapshot_rows,
    render_snapshot_warning_lines,
    render_warning,
)
from .progress import ConsoleProgressReporter
from .snapshot_catalog_service import discover_snapshots


def run_repl(*, resolved_paths: ResolvedPaths, ignore_rule_set: IgnoreRuleSet) -> int:
    print(render_app_banner())
    print()
    for line in render_loaded_parameters(
        resolved_paths=resolved_paths,
        ignore_rule_set=ignore_rule_set,
    ):
        print(line)

    while True:
        print()
        print(render_main_menu())
        choice_raw = _read_line("Select option: ")
        if choice_raw is None:
            print("Exiting.")
            return 0
        choice = choice_raw.strip()

        if choice == "1":
            _run_archive_action(
                resolved_paths=resolved_paths,
                ignore_rule_set=ignore_rule_set,
            )
            continue

        if choice == "2":
            _run_extract_action(resolved_paths=resolved_paths)
            continue

        if choice == "3":
            print("Exiting.")
            return 0

        print(render_error("Invalid menu selection. Use 1, 2, or 3."))


def _run_archive_action(
    *, resolved_paths: ResolvedPaths, ignore_rule_set: IgnoreRuleSet
) -> None:
    progress = ConsoleProgressReporter()

    print()
    comment_raw_value = _read_line("Archive comment: ")
    if comment_raw_value is None:
        print(render_error("Comment is required."))
        return
    comment_raw = comment_raw_value

    try:
        archive_result = create_snapshot(
            resolved_paths=resolved_paths,
            ignore_rule_set=ignore_rule_set,
            comment_raw=comment_raw,
            on_scan_progress=progress.report_scanned,
            on_archive_progress=progress.report_archived,
        )
    except RevzipError as exc:
        progress.close_open_lines()
        print()
        print(render_error(str(exc)))
        return

    if archive_result.skipped_symlinks_rel:
        print()
        for symlink_rel in archive_result.skipped_symlinks_rel:
            print(render_warning(f"Skipped symlink: {symlink_rel}"))
    print()
    print(
        "Archived "
        f"{archive_result.archived_file_count} file(s) and "
        f"{archive_result.empty_directory_count} empty directory(s)."
    )
    print(f"Created ZIP: {archive_result.zip_path.name}")
    print(f"Created metadata: {archive_result.metadata_path.name}")


def _run_extract_action(*, resolved_paths: ResolvedPaths) -> None:
    snapshot_records, snapshot_warnings = discover_snapshots(
        dest_dir_abs=resolved_paths.dest_dir_abs
    )
    if snapshot_warnings:
        print()
        for warning_line in render_snapshot_warning_lines(snapshot_warnings):
            print(warning_line)

    if not snapshot_records:
        print()
        print("No valid snapshots available for extraction.")
        return

    print()
    print("Available snapshots:")
    for row in render_snapshot_rows(snapshot_records):
        print(row)

    print()
    selected_record = _prompt_snapshot_selection(snapshot_records)
    if selected_record is None:
        return

    print()
    confirmation_raw = _read_line("Type yes to restore the selected snapshot: ")
    if confirmation_raw is None:
        print("Restore canceled.")
        return
    confirmation = confirmation_raw.strip()
    if confirmation != "yes":
        print("Restore canceled.")
        return

    try:
        restore_result = restore_snapshot(
            source_dir_abs=resolved_paths.source_dir_abs,
            snapshot_record=selected_record,
        )
    except RevzipError as exc:
        print(render_error(str(exc)))
        return

    print(
        "Restore complete "
        f"from {restore_result.selected_zip_path.name}: "
        f"{restore_result.restored_file_count} file(s), "
        f"{restore_result.restored_empty_directory_count} empty directory(s)."
    )


def _prompt_snapshot_selection(
    snapshot_records: list[SnapshotRecord],
) -> SnapshotRecord | None:
    raw_selection_value = _read_line("Select snapshot number: ")
    if raw_selection_value is None:
        print(render_error("Selection is required."))
        return None
    raw_selection = raw_selection_value.strip()
    if raw_selection == "":
        print(render_error("Selection is required."))
        return None
    if not raw_selection.isdigit():
        print(render_error("Selection must be a number."))
        return None

    selected_index = int(raw_selection)
    if selected_index < 1 or selected_index > len(snapshot_records):
        print(render_error("Selection is out of range."))
        return None

    return snapshot_records[selected_index - 1]


def _read_line(prompt: str) -> str | None:
    try:
        return input(prompt)
    except EOFError:
        return None
