from __future__ import annotations

from collections import OrderedDict
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from revzip.errors import MetadataError
from revzip.metadata_gateway import read_snapshot_metadata, write_snapshot_metadata
from revzip.models import SnapshotMetadata
from revzip.timestamps import format_created_at, format_created_utc


def test_read_snapshot_metadata_rejects_non_string_archived_file_entries(
    tmp_path: Path,
) -> None:
    created_utc_dt = datetime(2026, 2, 25, 9, 10, 11, 123456, tzinfo=timezone.utc)
    metadata_path = tmp_path / "snapshot.json"
    metadata_path.write_text(
        json.dumps(
            {
                "created_utc": format_created_utc(created_utc_dt),
                "created_at": format_created_at(created_utc_dt),
                "comment": "ok",
                "comment_filename_segment": "ok",
                "zip_filename": "snapshot.zip",
                "archived_files": ["file.txt", 123],
                "empty_directories": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        MetadataError,
        match="Metadata key 'archived_files' must be a list of strings",
    ):
        read_snapshot_metadata(metadata_path_abs=metadata_path)


def test_write_snapshot_metadata_uses_fixed_logical_key_order(tmp_path: Path) -> None:
    created_utc_dt = datetime(2026, 2, 25, 9, 10, 11, 123456, tzinfo=timezone.utc)
    metadata_path = tmp_path / "snapshot.json"

    write_snapshot_metadata(
        metadata_path_abs=metadata_path,
        snapshot_metadata=SnapshotMetadata(
            created_utc=format_created_utc(created_utc_dt),
            created_at=format_created_at(created_utc_dt),
            comment="snapshot",
            comment_filename_segment="snapshot",
            zip_filename="snapshot.zip",
            archived_files=["alpha.txt"],
            empty_directories=["empty"],
        ),
    )

    payload = json.loads(
        metadata_path.read_text(encoding="utf-8"),
        object_pairs_hook=OrderedDict,
    )

    assert list(payload.keys()) == [
        "created_utc",
        "created_at",
        "comment",
        "comment_filename_segment",
        "zip_filename",
        "archived_files",
        "empty_directories",
    ]
