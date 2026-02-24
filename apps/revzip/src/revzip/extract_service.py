"""Extract workflow orchestration."""

from __future__ import annotations

from pathlib import Path

from .fs_gateway import clear_and_recreate_directory, count_regular_files_and_empty_directories
from .models import RestoreResult, SnapshotRecord
from .zip_gateway import extract_snapshot_zip, verify_zip_integrity


def restore_snapshot(
    *, source_dir_abs: Path, snapshot_record: SnapshotRecord
) -> RestoreResult:
    verify_zip_integrity(snapshot_record.zip_path)
    clear_and_recreate_directory(source_dir_abs)
    extract_snapshot_zip(
        zip_path_abs=snapshot_record.zip_path,
        target_dir_abs=source_dir_abs,
    )
    restored_file_count, restored_empty_directory_count = (
        count_regular_files_and_empty_directories(source_dir_abs)
    )
    return RestoreResult(
        selected_zip_path=snapshot_record.zip_path,
        restored_file_count=restored_file_count,
        restored_empty_directory_count=restored_empty_directory_count,
    )
