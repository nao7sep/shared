"""Tests for pydeli.archive_store module."""


from packaging.version import Version

from pydeli.archive_store import archive_artifacts
from pydeli.models import BuildArtifact


class TestArchiveArtifacts:
    def test_creates_version_dir(self, tmp_path):
        # Create fake artifacts
        src_dir = tmp_path / "dist"
        src_dir.mkdir()
        (src_dir / "pkg-0.1.0.tar.gz").write_text("fake tarball")
        (src_dir / "pkg-0.1.0-py3-none-any.whl").write_text("fake wheel")

        artifacts = [
            BuildArtifact(path=src_dir / "pkg-0.1.0.tar.gz", filename="pkg-0.1.0.tar.gz"),
            BuildArtifact(path=src_dir / "pkg-0.1.0-py3-none-any.whl", filename="pkg-0.1.0-py3-none-any.whl"),
        ]

        archive_dir = tmp_path / "archive"
        result = archive_artifacts(archive_dir, Version("0.1.0"), artifacts)

        assert result == archive_dir / "0.1.0"
        assert (result / "pkg-0.1.0.tar.gz").exists()
        assert (result / "pkg-0.1.0-py3-none-any.whl").exists()

    def test_overwrites_existing(self, tmp_path):
        src_dir = tmp_path / "dist"
        src_dir.mkdir()
        (src_dir / "pkg-0.1.0.tar.gz").write_text("version1")
        artifacts = [BuildArtifact(path=src_dir / "pkg-0.1.0.tar.gz", filename="pkg-0.1.0.tar.gz")]

        archive_dir = tmp_path / "archive"
        archive_artifacts(archive_dir, Version("0.1.0"), artifacts)

        # Overwrite with new content
        (src_dir / "pkg-0.1.0.tar.gz").write_text("version2")
        archive_artifacts(archive_dir, Version("0.1.0"), artifacts)

        assert (archive_dir / "0.1.0" / "pkg-0.1.0.tar.gz").read_text() == "version2"
