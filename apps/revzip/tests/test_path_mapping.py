from __future__ import annotations

from pathlib import Path

import pytest

from revzip.errors import PathMappingError, StartupValidationError
from revzip.path_mapping import map_path_argument, resolve_startup_paths


def test_map_path_argument_rejects_pure_relative_path(tmp_path: Path) -> None:
    with pytest.raises(PathMappingError):
        map_path_argument(
            raw_path="relative/path",
            app_root_abs=tmp_path,
            argument_name="--source",
        )


def test_resolve_startup_paths_creates_dest_directory(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    dest_dir = tmp_path / "dest"

    resolved = resolve_startup_paths(
        source_arg_raw=str(source_dir),
        dest_arg_raw=str(dest_dir),
        ignore_arg_raw=None,
        app_root_abs=tmp_path,
    )

    assert resolved.dest_dir_abs == dest_dir.resolve(strict=False)
    assert dest_dir.exists()
    assert dest_dir.is_dir()


def test_resolve_startup_paths_rejects_source_dest_overlap(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    overlapping_dest = source_dir / "snapshots"

    with pytest.raises(StartupValidationError):
        resolve_startup_paths(
            source_arg_raw=str(source_dir),
            dest_arg_raw=str(overlapping_dest),
            ignore_arg_raw=None,
            app_root_abs=tmp_path,
        )
