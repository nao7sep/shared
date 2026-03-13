from __future__ import annotations

import subprocess

import pytest

from pydeli.errors import PublishError
from pydeli.models import BuildArtifact, RegistryTarget
from pydeli.publisher import TESTPYPI_UPLOAD_URL, UV_PUBLISH_TOKEN_ENV, publish


class TestPublisher:
    """Publish wrapper: command construction and error handling."""

    def test_testpypi_includes_publish_url(self, tmp_path, monkeypatch) -> None:
        """TestPyPI target should pass --publish-url to uv publish."""
        captured_cmds: list[list[str]] = []

        def mock_run(cmd, **kwargs):
            captured_cmds.append(cmd)

        monkeypatch.setattr("pydeli.publisher.subprocess.run", mock_run)

        whl = tmp_path / "app.whl"
        whl.write_text("data")
        publish([BuildArtifact(file_path=whl)], RegistryTarget.TESTPYPI, "tok")

        cmd = captured_cmds[0]
        assert "--publish-url" in cmd
        assert TESTPYPI_UPLOAD_URL in cmd

    def test_pypi_does_not_include_publish_url(self, tmp_path, monkeypatch) -> None:
        """PyPI target should not pass --publish-url (uses default)."""
        captured_cmds: list[list[str]] = []

        def mock_run(cmd, **kwargs):
            captured_cmds.append(cmd)

        monkeypatch.setattr("pydeli.publisher.subprocess.run", mock_run)

        whl = tmp_path / "app.whl"
        whl.write_text("data")
        publish([BuildArtifact(file_path=whl)], RegistryTarget.PYPI, "tok")

        cmd = captured_cmds[0]
        assert "--publish-url" not in cmd

    def test_token_injected_via_env_not_cli(self, tmp_path, monkeypatch) -> None:
        """Token must be in the environment, never in the command args."""
        captured_envs: list[dict] = []
        captured_cmds: list[list[str]] = []

        def mock_run(cmd, **kwargs):
            captured_cmds.append(cmd)
            captured_envs.append(kwargs.get("env", {}))

        monkeypatch.setattr("pydeli.publisher.subprocess.run", mock_run)

        whl = tmp_path / "app.whl"
        whl.write_text("data")
        token = "pypi-secret-token-abc"
        publish([BuildArtifact(file_path=whl)], RegistryTarget.PYPI, token)

        # Token must NOT appear in the command line
        full_cmd = " ".join(captured_cmds[0])
        assert token not in full_cmd

        # Token MUST be in the environment
        assert captured_envs[0][UV_PUBLISH_TOKEN_ENV] == token

    def test_failure_raises_with_stderr(self, tmp_path, monkeypatch) -> None:
        """Publish failure should include uv's error output."""

        def mock_run(cmd, **kwargs):
            raise subprocess.CalledProcessError(
                returncode=1,
                cmd=cmd,
                stderr="403 Forbidden: invalid token",
            )

        monkeypatch.setattr("pydeli.publisher.subprocess.run", mock_run)

        whl = tmp_path / "app.whl"
        whl.write_text("data")

        with pytest.raises(PublishError, match="403 Forbidden"):
            publish([BuildArtifact(file_path=whl)], RegistryTarget.PYPI, "bad-tok")
