from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from revzip.errors import ZipIntegrityError
from revzip.extract_service import restore_snapshot
from revzip.models import SnapshotMetadata, SnapshotRecord
from revzip.timestamps import format_created_at, format_created_utc


def test_restore_snapshot_keeps_existing_files_when_zip_is_invalid(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    existing_file = source_dir / "keep.txt"
    existing_file.write_text("keep", encoding="utf-8")

    broken_zip = tmp_path / "broken.zip"
    broken_zip.write_text("not a zip", encoding="utf-8")

    created_utc_dt = datetime(2026, 2, 25, 9, 10, 11, 123456, tzinfo=timezone.utc)
    snapshot_record = SnapshotRecord(
        metadata_path=tmp_path / "broken.json",
        zip_path=broken_zip,
        metadata=SnapshotMetadata(
            created_utc=format_created_utc(created_utc_dt),
            created_at=format_created_at(created_utc_dt),
            comment="broken",
            comment_filename_segment="broken",
            zip_filename=broken_zip.name,
            archived_files=[],
            empty_directories=[],
        ),
        created_utc_dt=created_utc_dt,
    )

    with pytest.raises(ZipIntegrityError):
        restore_snapshot(source_dir_abs=source_dir, snapshot_record=snapshot_record)

    assert existing_file.read_text(encoding="utf-8") == "keep"
