"""Archive store: version-subdirectory creation and artifact archival.

Archives live under <archive-dir>/<version>/.
Files for the same version are silently overwritten without confirmation.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from packaging.version import Version

from .models import BuildArtifact


def archive_artifacts(
    archive_dir: Path, version: Version, artifacts: list[BuildArtifact]
) -> Path:
    """Copy build artifacts into <archive-dir>/<version>/.

    Returns the version-specific archive subdirectory.
    """
    version_dir = archive_dir / str(version)
    version_dir.mkdir(parents=True, exist_ok=True)

    for artifact in artifacts:
        dest = version_dir / artifact.filename
        shutil.copy2(str(artifact.path), str(dest))

    return version_dir
