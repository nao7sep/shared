from __future__ import annotations

import shutil
from pathlib import Path

from .models import BuildArtifact


def archive(artifacts: list[BuildArtifact], archive_dir: Path, app_name: str) -> Path:
    """Copy build artifacts to <archive_dir>/<app_name>/.

    Creates the directory if it does not exist. Silently overwrites existing
    files with the same names. Returns the archive destination directory.
    """
    dest_dir = archive_dir / app_name
    dest_dir.mkdir(parents=True, exist_ok=True)

    for artifact in artifacts:
        dest_file = dest_dir / artifact.file_path.name
        shutil.copy2(artifact.file_path, dest_file)

    return dest_dir
