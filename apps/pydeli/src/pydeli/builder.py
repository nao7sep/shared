from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .errors import BuildError
from .models import BuildArtifact


def build(app_dir: Path) -> list[BuildArtifact]:
    """Run uv build in the target app directory and return the artifacts.

    Cleans the dist/ directory before building to ensure only fresh artifacts
    are present. Raises BuildError if the build fails.
    """
    dist_dir = app_dir / "dist"

    # Clean previous build output so we only pick up fresh artifacts.
    if dist_dir.exists():
        shutil.rmtree(dist_dir)

    try:
        subprocess.run(
            ["uv", "build"],
            cwd=app_dir,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise BuildError("uv is not installed or not found on PATH.") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else "No error output."
        raise BuildError(f"uv build failed:\n{stderr}") from exc

    if not dist_dir.exists():
        raise BuildError(f"Build completed but dist/ directory not found: {dist_dir}")

    artifacts = [
        BuildArtifact(file_path=p)
        for p in sorted(dist_dir.iterdir())
        if p.is_file() and (p.suffix in (".whl", ".gz"))
    ]

    if not artifacts:
        raise BuildError(f"Build completed but no .whl or .tar.gz files found in {dist_dir}")

    return artifacts
