"""Archive workflow orchestration."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from .comment_sanitizer import validate_and_sanitize_comment
from .errors import ArchiveCollisionError, ArchiveEmptyError
from .fs_gateway import collect_archive_inventory
from .metadata_gateway import write_snapshot_metadata
from .models import ArchiveResult, IgnoreRuleSet, ResolvedPaths, SnapshotMetadata
from .timestamps import format_created_at, format_created_utc, format_filename_timestamp, utc_now
from .zip_gateway import write_snapshot_zip


def create_snapshot(
    *,
    resolved_paths: ResolvedPaths,
    ignore_rule_set: IgnoreRuleSet,
    comment_raw: str,
    now_utc_dt: datetime | None = None,
    on_scan_progress: Callable[[int, int, bool], None] | None = None,
    on_archive_progress: Callable[[int, int, bool], None] | None = None,
) -> ArchiveResult:
    comment, comment_filename_segment = validate_and_sanitize_comment(comment_raw)
    on_directory_scanned = None
    if on_scan_progress is not None:
        on_directory_scanned = (
            lambda scanned_dirs, scanned_files: on_scan_progress(
                scanned_dirs, scanned_files, False
            )
        )

    archive_inventory = collect_archive_inventory(
        source_dir_abs=resolved_paths.source_dir_abs,
        raw_source_argument=resolved_paths.source_arg_raw,
        ignore_rule_set=ignore_rule_set,
        on_directory_scanned=on_directory_scanned,
    )
    if on_scan_progress is not None:
        on_scan_progress(
            archive_inventory.scanned_directories_count,
            archive_inventory.scanned_files_count,
            True,
        )

    archived_file_count = len(archive_inventory.archived_files_rel)
    empty_directory_count = len(archive_inventory.empty_directories_rel)
    if archived_file_count == 0 and empty_directory_count == 0:
        raise ArchiveEmptyError("No files or empty directories matched for archiving.")

    effective_now_utc_dt = now_utc_dt if now_utc_dt is not None else utc_now()
    filename_timestamp = format_filename_timestamp(effective_now_utc_dt)
    created_utc = format_created_utc(effective_now_utc_dt)
    created_at = format_created_at(effective_now_utc_dt)
    base_name = f"{filename_timestamp}_{comment_filename_segment}"

    zip_path = resolved_paths.dest_dir_abs / f"{base_name}.zip"
    metadata_path = resolved_paths.dest_dir_abs / f"{base_name}.json"
    _validate_no_collision(zip_path=zip_path, metadata_path=metadata_path)

    snapshot_metadata = SnapshotMetadata(
        created_utc=created_utc,
        created_at=created_at,
        comment=comment,
        comment_filename_segment=comment_filename_segment,
        zip_filename=zip_path.name,
        archived_files=[str(path_rel) for path_rel in archive_inventory.archived_files_rel],
        empty_directories=[
            str(path_rel) for path_rel in archive_inventory.empty_directories_rel
        ],
    )

    try:
        archived_files_written = 0

        def _on_file_archived(written_count: int, total_count: int) -> None:
            nonlocal archived_files_written
            archived_files_written = written_count
            if on_archive_progress is not None:
                on_archive_progress(written_count, total_count, False)

        write_snapshot_zip(
            source_dir_abs=resolved_paths.source_dir_abs,
            zip_path_abs=zip_path,
            archived_files_rel=archive_inventory.archived_files_rel,
            empty_directories_rel=archive_inventory.empty_directories_rel,
            on_file_archived=(
                _on_file_archived
                if on_archive_progress is not None
                else None
            ),
        )
        if on_archive_progress is not None:
            on_archive_progress(archived_files_written, archived_file_count, True)
        write_snapshot_metadata(
            metadata_path_abs=metadata_path,
            snapshot_metadata=snapshot_metadata,
        )
    except Exception:
        zip_path.unlink(missing_ok=True)
        metadata_path.unlink(missing_ok=True)
        raise

    return ArchiveResult(
        zip_path=zip_path,
        metadata_path=metadata_path,
        archived_file_count=archived_file_count,
        empty_directory_count=empty_directory_count,
        created_utc=created_utc,
        skipped_symlinks_rel=archive_inventory.skipped_symlinks_rel,
    )


def _validate_no_collision(*, zip_path: Path, metadata_path: Path) -> None:
    if zip_path.exists() or metadata_path.exists():
        raise ArchiveCollisionError(
            "Snapshot file name collision detected. "
            f"Refusing to overwrite: {zip_path.name} / {metadata_path.name}"
        )
