from __future__ import annotations

import os
import subprocess

from .errors import PublishError
from .models import BuildArtifact, RegistryTarget

TESTPYPI_UPLOAD_URL = "https://test.pypi.org/legacy/"
UV_PUBLISH_TOKEN_ENV = "UV_PUBLISH_TOKEN"


def publish(
    artifacts: list[BuildArtifact],
    target: RegistryTarget,
    token: str,
) -> None:
    """Upload build artifacts to the target registry using uv publish.

    The token is injected via the UV_PUBLISH_TOKEN environment variable.
    Raises PublishError if the upload fails.
    """
    artifact_paths = [str(a.file_path) for a in artifacts]

    cmd = ["uv", "publish"]
    if target is RegistryTarget.TESTPYPI:
        cmd.extend(["--publish-url", TESTPYPI_UPLOAD_URL])
    cmd.extend(artifact_paths)

    env = {**os.environ, UV_PUBLISH_TOKEN_ENV: token}

    try:
        subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
    except FileNotFoundError as exc:
        raise PublishError("uv is not installed or not found on PATH.") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else "No error output."
        raise PublishError(
            f"uv publish to {target.display_name} failed:\n{stderr}"
        ) from exc
