from __future__ import annotations

import subprocess

import pytest

from pydeli.builder import build
from pydeli.errors import BuildError


class TestBuilder:
    """Build wrapper edge cases via mocked subprocess."""

    def test_uv_not_found_raises(self, tmp_path, monkeypatch) -> None:
        """Missing uv binary should raise BuildError with clear message."""
        dist = tmp_path / "dist"
        # If dist exists from a previous build, clean it
        if dist.exists():
            import shutil
            shutil.rmtree(dist)

        def mock_run(*args, **kwargs):
            raise FileNotFoundError("uv")

        monkeypatch.setattr("pydeli.builder.subprocess.run", mock_run)

        with pytest.raises(BuildError, match="not installed"):
            build(tmp_path)

    def test_build_failure_includes_stderr(self, tmp_path, monkeypatch) -> None:
        """Failed build should include uv's error output in the exception."""

        def mock_run(*args, **kwargs):
            raise subprocess.CalledProcessError(
                returncode=1,
                cmd=["uv", "build"],
                stderr="error: missing pyproject.toml",
            )

        monkeypatch.setattr("pydeli.builder.subprocess.run", mock_run)

        with pytest.raises(BuildError, match="missing pyproject.toml"):
            build(tmp_path)

    def test_no_artifacts_after_build_raises(self, tmp_path, monkeypatch) -> None:
        """Build succeeds but dist/ is empty — should raise."""
        dist = tmp_path / "dist"
        dist.mkdir(exist_ok=True)

        def mock_run(*args, **kwargs):
            # Simulate successful build but leave dist empty
            dist.mkdir(exist_ok=True)

        monkeypatch.setattr("pydeli.builder.subprocess.run", mock_run)

        with pytest.raises(BuildError, match="no .whl or .tar.gz"):
            build(tmp_path)

    def test_only_picks_whl_and_targz(self, tmp_path, monkeypatch) -> None:
        """Build output should filter out non-artifact files."""
        dist = tmp_path / "dist"

        def mock_run(*args, **kwargs):
            dist.mkdir(exist_ok=True)
            (dist / "myapp-1.0.0-py3-none-any.whl").write_text("wheel")
            (dist / "myapp-1.0.0.tar.gz").write_text("tarball")
            (dist / "build-log.txt").write_text("log")  # should be ignored

        monkeypatch.setattr("pydeli.builder.subprocess.run", mock_run)

        artifacts = build(tmp_path)
        names = {a.file_path.name for a in artifacts}
        assert names == {"myapp-1.0.0-py3-none-any.whl", "myapp-1.0.0.tar.gz"}
