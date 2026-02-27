from __future__ import annotations

import zipfile
from datetime import datetime, timezone
from pathlib import Path

from revzip.metadata_gateway import write_snapshot_metadata
from revzip.models import SnapshotMetadata
from revzip.snapshot_catalog_service import discover_snapshots
from revzip.timestamps import format_created_at, format_created_utc


def test_discover_snapshots_warns_and_keeps_valid_entries(tmp_path: Path) -> None:
    valid_now_utc = datetime(2026, 2, 25, 9, 10, 11, 123456, tzinfo=timezone.utc)
    valid_zip = tmp_path / "valid.zip"
    with zipfile.ZipFile(valid_zip, mode="w") as zf:
        zf.writestr("file.txt", "hello")
    invalid_created_at_zip = tmp_path / "invalid-created-at.zip"
    with zipfile.ZipFile(invalid_created_at_zip, mode="w") as zf:
        zf.writestr("file.txt", "hello")

    write_snapshot_metadata(
        metadata_path_abs=tmp_path / "valid.json",
        snapshot_metadata=SnapshotMetadata(
            created_utc=format_created_utc(valid_now_utc),
            created_at=format_created_at(valid_now_utc),
            comment="ok",
            comment_filename_segment="ok",
            zip_filename="valid.zip",
            archived_files=["file.txt"],
            empty_directories=[],
        ),
    )

    (tmp_path / "broken.json").write_text("{ bad json", encoding="utf-8")

    write_snapshot_metadata(
        metadata_path_abs=tmp_path / "orphan.json",
        snapshot_metadata=SnapshotMetadata(
            created_utc=format_created_utc(valid_now_utc),
            created_at=format_created_at(valid_now_utc),
            comment="orphan",
            comment_filename_segment="orphan",
            zip_filename="orphan.zip",
            archived_files=[],
            empty_directories=[],
        ),
    )
    write_snapshot_metadata(
        metadata_path_abs=tmp_path / "invalid-created-at.json",
        snapshot_metadata=SnapshotMetadata(
            created_utc=format_created_utc(valid_now_utc),
            created_at="2026/02/25 18:10:11",
            comment="bad created_at",
            comment_filename_segment="bad-created-at",
            zip_filename="invalid-created-at.zip",
            archived_files=["file.txt"],
            empty_directories=[],
        ),
    )

    records, warnings = discover_snapshots(dest_dir_abs=tmp_path)

    assert len(records) == 1
    assert records[0].zip_path.name == "valid.zip"
    assert len(warnings) == 3
    warning_text = "\n".join(w.message for w in warnings)
    assert "broken.json" in warning_text
    assert "orphan.json" in warning_text
    assert "invalid-created-at.json" in warning_text
    assert "Invalid created_at timestamp in metadata" in warning_text
