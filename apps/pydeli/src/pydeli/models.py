from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class RegistryTarget(Enum):
    TESTPYPI = "testpypi"
    PYPI = "pypi"

    @property
    def display_name(self) -> str:
        if self is RegistryTarget.TESTPYPI:
            return "TestPyPI"
        return "PyPI"


class RunMode(Enum):
    DRY = "dry"
    WET = "wet"


@dataclass(frozen=True)
class VersionSource:
    """A version string discovered in a specific file."""

    file_path: Path
    version_string: str


@dataclass(frozen=True)
class BuildArtifact:
    """A build output file (wheel or sdist)."""

    file_path: Path
