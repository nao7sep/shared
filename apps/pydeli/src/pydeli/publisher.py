"""Upload orchestration for TestPyPI and PyPI via uv publish.

Secrets are passed only via the subprocess environment boundary.
They are never logged, echoed, or placed on the command line.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from packaging.version import Version

from .errors import PublishError
from .models import BuildArtifact, PublishResult, Registry


def publish_to_registry(
    registry: Registry,
    artifacts: list[BuildArtifact],
    token: str,
    version: Version,
) -> PublishResult:
    """Publish artifacts to the specified registry using uv publish.

    The token is passed via UV_PUBLISH_TOKEN environment variable.
    """
    artifact_paths = [str(a.path) for a in artifacts]

    env_extra = {
        "UV_PUBLISH_TOKEN": token,
    }

    cmd = ["uv", "publish", "--publish-url", registry.upload_url] + artifact_paths

    try:
        import os

        env = {**os.environ, **env_extra}
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )
    except FileNotFoundError:
        raise PublishError("uv is not installed or not on PATH.")
    except subprocess.TimeoutExpired:
        raise PublishError(
            f"Publish to {registry.display_name} timed out after 120 seconds."
        )

    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise PublishError(
            f"Publish to {registry.display_name} failed (exit {result.returncode}):\n{stderr}"
        )

    return PublishResult(
        registry=registry,
        version=version,
        success=True,
        message=f"Successfully published {version} to {registry.display_name}.",
    )


def publish_from_archive(
    registry: Registry,
    archive_version_dir: Path,
    token: str,
    version: Version,
) -> PublishResult:
    """Publish all artifacts from an archive version directory."""
    artifacts: list[BuildArtifact] = []
    for path in sorted(archive_version_dir.iterdir()):
        if path.is_file() and (path.suffix in {".whl", ".gz"}):
            artifacts.append(BuildArtifact(path=path, filename=path.name))

    if not artifacts:
        raise PublishError(f"No publishable artifacts found in {archive_version_dir}")

    return publish_to_registry(registry, artifacts, token, version)
