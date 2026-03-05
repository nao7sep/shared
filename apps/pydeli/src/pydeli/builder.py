"""Build execution via uv build and artifact collection."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from .errors import BuildError
from .models import BuildArtifact, BuildResult


def build_app(app_dir: Path) -> BuildResult:
    """Run uv build in the target app directory and collect artifacts.

    Uses a temporary dist directory to avoid polluting the app tree,
    then returns the artifacts with their original filenames.
    """
    with tempfile.TemporaryDirectory(prefix="pydeli-build-") as tmp:
        dist_dir = Path(tmp) / "dist"
        dist_dir.mkdir()

        try:
            result = subprocess.run(
                ["uv", "build", "--out-dir", str(dist_dir)],
                cwd=str(app_dir),
                capture_output=True,
                text=True,
                timeout=300,
            )
        except FileNotFoundError:
            raise BuildError(
                "uv is not installed or not on PATH. Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh"
            )
        except subprocess.TimeoutExpired:
            raise BuildError("Build timed out after 300 seconds.")

        if result.returncode != 0:
            stderr = result.stderr.strip()
            raise BuildError(f"uv build failed (exit {result.returncode}):\n{stderr}")

        artifacts: list[BuildArtifact] = []
        for path in sorted(dist_dir.iterdir()):
            if path.is_file():
                artifacts.append(BuildArtifact(path=path, filename=path.name))

        if not artifacts:
            raise BuildError("uv build produced no artifacts.")

        return BuildResult(artifacts=artifacts, dist_dir=dist_dir)
