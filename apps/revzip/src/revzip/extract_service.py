"""Extract workflow orchestration."""

from __future__ import annotations

from pathlib import Path

from .fs_gateway import (
    count_regular_files_and_empty_directories,
    create_restore_staging_directory,
    remove_directory_tree,
    replace_directory_with_staging,
)
from .models import RestoreResult, SnapshotRecord
from .zip_gateway import extract_snapshot_zip, verify_zip_integrity


def restore_snapshot(
    *, source_dir_abs: Path, snapshot_record: SnapshotRecord
) -> RestoreResult:
    verify_zip_integrity(snapshot_record.zip_path)
    staging_dir_abs = create_restore_staging_directory(source_dir_abs)
    try:
        extract_snapshot_zip(
            zip_path_abs=snapshot_record.zip_path,
            target_dir_abs=staging_dir_abs,
        )
        restored_file_count, restored_empty_directory_count = (
            count_regular_files_and_empty_directories(staging_dir_abs)
        )
        replace_directory_with_staging(
            target_dir_abs=source_dir_abs,
            staging_dir_abs=staging_dir_abs,
        )
    except Exception:
        if staging_dir_abs.exists():
            remove_directory_tree(staging_dir_abs)
        raise

    return RestoreResult(
        selected_zip_path=snapshot_record.zip_path,
        restored_file_count=restored_file_count,
        restored_empty_directory_count=restored_empty_directory_count,
    )
