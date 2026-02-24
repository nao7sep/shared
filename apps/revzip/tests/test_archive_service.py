from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from revzip.archive_service import create_snapshot
from revzip.errors import ArchiveCollisionError
from revzip.ignore_rules import load_ignore_rule_set
from revzip.path_mapping import resolve_startup_paths


def test_create_snapshot_fails_on_same_name_collision(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    dest_dir = tmp_path / "dest"
    source_dir.mkdir()
    dest_dir.mkdir()
    (source_dir / "hello.txt").write_text("hello", encoding="utf-8")

    resolved_paths = resolve_startup_paths(
        source_arg_raw=str(source_dir),
        dest_arg_raw=str(dest_dir),
        ignore_arg_raw=None,
        app_root_abs=tmp_path,
    )
    ignore_rule_set = load_ignore_rule_set(None)
    fixed_now_utc = datetime(2026, 2, 25, 4, 5, 6, tzinfo=timezone.utc)

    create_snapshot(
        resolved_paths=resolved_paths,
        ignore_rule_set=ignore_rule_set,
        comment_raw="same comment",
        now_utc_dt=fixed_now_utc,
    )

    with pytest.raises(ArchiveCollisionError):
        create_snapshot(
            resolved_paths=resolved_paths,
            ignore_rule_set=ignore_rule_set,
            comment_raw="same comment",
            now_utc_dt=fixed_now_utc,
        )
