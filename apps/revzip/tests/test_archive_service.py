from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

import revzip.archive_service as archive_service
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

    archive_service.create_snapshot(
        resolved_paths=resolved_paths,
        ignore_rule_set=ignore_rule_set,
        comment_raw="same comment",
        now_utc_dt=fixed_now_utc,
    )

    with pytest.raises(ArchiveCollisionError):
        archive_service.create_snapshot(
            resolved_paths=resolved_paths,
            ignore_rule_set=ignore_rule_set,
            comment_raw="same comment",
            now_utc_dt=fixed_now_utc,
        )


def test_create_snapshot_progress_callbacks_report_scan_and_archive(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "source"
    dest_dir = tmp_path / "dest"
    source_dir.mkdir()
    dest_dir.mkdir()
    (source_dir / "a.txt").write_text("a", encoding="utf-8")
    (source_dir / "b.txt").write_text("b", encoding="utf-8")
    (source_dir / "empty").mkdir()

    resolved_paths = resolve_startup_paths(
        source_arg_raw=str(source_dir),
        dest_arg_raw=str(dest_dir),
        ignore_arg_raw=None,
        app_root_abs=tmp_path,
    )
    ignore_rule_set = load_ignore_rule_set(None)
    fixed_now_utc = datetime(2026, 2, 25, 4, 5, 6, tzinfo=timezone.utc)

    scan_events: list[tuple[int, int, bool]] = []
    archive_events: list[tuple[int, int, bool]] = []

    archive_service.create_snapshot(
        resolved_paths=resolved_paths,
        ignore_rule_set=ignore_rule_set,
        comment_raw="progress",
        now_utc_dt=fixed_now_utc,
        on_scan_progress=lambda dirs, files, final: scan_events.append(
            (dirs, files, final)
        ),
        on_archive_progress=lambda archived, total, final: archive_events.append(
            (archived, total, final)
        ),
    )

    assert scan_events
    assert scan_events[-1][2] is True
    assert archive_events[-1] == (2, 2, True)


def test_create_snapshot_removes_partial_outputs_when_metadata_write_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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

    def _fail_write_snapshot_metadata(**_: object) -> None:
        raise RuntimeError("metadata write failed")

    monkeypatch.setattr(
        archive_service,
        "write_snapshot_metadata",
        _fail_write_snapshot_metadata,
    )

    with pytest.raises(RuntimeError, match="metadata write failed"):
        archive_service.create_snapshot(
            resolved_paths=resolved_paths,
            ignore_rule_set=ignore_rule_set,
            comment_raw="cleanup",
            now_utc_dt=fixed_now_utc,
        )

    assert list(dest_dir.iterdir()) == []
