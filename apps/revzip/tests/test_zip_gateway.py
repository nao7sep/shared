from __future__ import annotations

from pathlib import Path

import pytest

from revzip.errors import ArchiveError
from revzip.zip_gateway import write_snapshot_zip


def test_write_snapshot_zip_rejects_duplicate_entry_paths(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "dup.txt").write_text("x", encoding="utf-8")

    with pytest.raises(ArchiveError):
        write_snapshot_zip(
            source_dir_abs=source_dir,
            zip_path_abs=tmp_path / "snapshot.zip",
            archived_files_rel=[Path("dup.txt"), Path("dup.txt")],
            empty_directories_rel=[],
        )
