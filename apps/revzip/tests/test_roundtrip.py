from __future__ import annotations

import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from revzip.archive_service import create_snapshot
from revzip.extract_service import restore_snapshot
from revzip.ignore_rules import load_ignore_rule_set
from revzip.path_mapping import resolve_startup_paths
from revzip.snapshot_catalog_service import discover_snapshots


def test_archive_and_extract_roundtrip(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    dest_dir = tmp_path / "dest"
    source_dir.mkdir()
    dest_dir.mkdir()

    (source_dir / "file_at_root.txt").write_text("root", encoding="utf-8")
    nested_dir = source_dir / "folder"
    nested_dir.mkdir()
    (nested_dir / "nested.txt").write_text("nested", encoding="utf-8")
    utf8_dir = source_dir / "日本語"
    utf8_dir.mkdir()
    (utf8_dir / "文字.txt").write_text("utf8", encoding="utf-8")
    (source_dir / "empty_dir").mkdir()
    ignored_dir = source_dir / "ignored-dir"
    ignored_dir.mkdir()
    (ignored_dir / "ignore.txt").write_text("ignore", encoding="utf-8")

    ignore_file = tmp_path / "ignore.txt"
    ignore_file.write_text("ignored-dir", encoding="utf-8")

    resolved_paths = resolve_startup_paths(
        source_arg_raw=str(source_dir),
        dest_arg_raw=str(dest_dir),
        ignore_arg_raw=str(ignore_file),
        app_root_abs=tmp_path,
    )
    ignore_rule_set = load_ignore_rule_set(ignore_file)
    fixed_now_utc = datetime(2026, 2, 25, 11, 12, 13, 654321, tzinfo=timezone.utc)

    archive_result = create_snapshot(
        resolved_paths=resolved_paths,
        ignore_rule_set=ignore_rule_set,
        comment_raw="  first line\nsecond line  ",
        now_utc_dt=fixed_now_utc,
    )

    assert archive_result.archived_file_count == 3
    assert archive_result.empty_directory_count == 1

    with zipfile.ZipFile(archive_result.zip_path, mode="r") as zf:
        entry_names = sorted(zf.namelist())
    assert "file_at_root.txt" in entry_names
    assert "folder/nested.txt" in entry_names
    assert "日本語/文字.txt" in entry_names
    assert "empty_dir/" in entry_names
    assert all(not name.startswith(f"{source_dir.name}/") for name in entry_names)

    metadata_payload = json.loads(
        archive_result.metadata_path.read_text(encoding="utf-8")
    )
    assert metadata_payload["comment"] == "first line\nsecond line"
    assert metadata_payload["archived_files"] == [
        "file_at_root.txt",
        str(Path("folder") / "nested.txt"),
        str(Path("日本語") / "文字.txt"),
    ]
    assert metadata_payload["empty_directories"] == [str(Path("empty_dir"))]

    shutil.rmtree(source_dir)
    source_dir.mkdir()
    (source_dir / "new-file.txt").write_text("new", encoding="utf-8")

    snapshot_records, snapshot_warnings = discover_snapshots(dest_dir_abs=dest_dir)
    assert not snapshot_warnings
    restore_snapshot(
        source_dir_abs=source_dir,
        snapshot_record=snapshot_records[0],
    )

    assert not (source_dir / "new-file.txt").exists()
    assert (source_dir / "file_at_root.txt").read_text(encoding="utf-8") == "root"
    assert (source_dir / "folder" / "nested.txt").read_text(encoding="utf-8") == "nested"
    assert (source_dir / "日本語" / "文字.txt").read_text(encoding="utf-8") == "utf8"
    assert (source_dir / "empty_dir").is_dir()
    assert not (source_dir / "ignored-dir").exists()
