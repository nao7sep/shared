from __future__ import annotations

import pytest

from pydeli.archiver import archive
from pydeli.models import BuildArtifact


class TestArchiver:
    """Archiving build artifacts to a destination directory."""

    def test_copies_artifacts(self, tmp_path: pytest.TempPathFactory) -> None:
        """Artifacts should be copied to <archive_dir>/<app_name>/."""
        src = tmp_path / "dist"
        src.mkdir()
        whl = src / "myapp-1.0.0-py3-none-any.whl"
        tar = src / "myapp-1.0.0.tar.gz"
        whl.write_text("wheel-content")
        tar.write_text("tarball-content")

        archive_root = tmp_path / "archives"
        artifacts = [BuildArtifact(file_path=whl), BuildArtifact(file_path=tar)]

        dest = archive(artifacts, archive_root, "myapp")

        assert dest == archive_root / "myapp"
        assert (dest / "myapp-1.0.0-py3-none-any.whl").read_text() == "wheel-content"
        assert (dest / "myapp-1.0.0.tar.gz").read_text() == "tarball-content"

    def test_creates_nested_directories(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        """Archive dir and app subdirectory should be created if missing."""
        src = tmp_path / "dist"
        src.mkdir()
        whl = src / "a.whl"
        whl.write_text("data")

        deep_root = tmp_path / "a" / "b" / "c"
        archive([BuildArtifact(file_path=whl)], deep_root, "myapp")

        assert (deep_root / "myapp" / "a.whl").exists()

    def test_silent_overwrite(self, tmp_path: pytest.TempPathFactory) -> None:
        """Re-archiving the same version should overwrite without error."""
        src = tmp_path / "dist"
        src.mkdir()
        whl = src / "app-1.0.0.whl"
        archive_root = tmp_path / "archives"

        # First archive
        whl.write_text("original")
        archive([BuildArtifact(file_path=whl)], archive_root, "app")
        assert (archive_root / "app" / "app-1.0.0.whl").read_text() == "original"

        # Second archive — overwrite
        whl.write_text("rebuilt")
        archive([BuildArtifact(file_path=whl)], archive_root, "app")
        assert (archive_root / "app" / "app-1.0.0.whl").read_text() == "rebuilt"

    def test_flat_structure_multiple_versions(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        """Artifacts from different versions coexist flat in the same directory."""
        src = tmp_path / "dist"
        src.mkdir()
        archive_root = tmp_path / "archives"

        v1 = src / "app-1.0.0.whl"
        v1.write_text("v1")
        archive([BuildArtifact(file_path=v1)], archive_root, "app")

        v2 = src / "app-2.0.0.whl"
        v2.write_text("v2")
        archive([BuildArtifact(file_path=v2)], archive_root, "app")

        assert (archive_root / "app" / "app-1.0.0.whl").read_text() == "v1"
        assert (archive_root / "app" / "app-2.0.0.whl").read_text() == "v2"
