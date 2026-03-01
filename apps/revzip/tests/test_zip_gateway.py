from __future__ import annotations

from pathlib import Path
import zipfile

import pytest

from revzip.errors import ArchiveError, ExtractError
from revzip.zip_gateway import extract_snapshot_zip, write_snapshot_zip


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


def test_extract_snapshot_zip_rejects_parent_traversal_entries(tmp_path: Path) -> None:
    zip_path = tmp_path / "unsafe.zip"
    target_dir = tmp_path / "target"
    target_dir.mkdir()

    with zipfile.ZipFile(zip_path, mode="w") as zf:
        zf.writestr("../escape.txt", "nope")

    with pytest.raises(ExtractError, match="Unsafe zip entry path"):
        extract_snapshot_zip(zip_path_abs=zip_path, target_dir_abs=target_dir)

    assert list(target_dir.iterdir()) == []
