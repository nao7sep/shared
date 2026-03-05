"""Typed data models for pydeli.

All structured data uses typed models. No long-lived raw dicts.
Internal timestamps are stored as UTC and named with *_utc.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from packaging.version import Version


class Registry(Enum):
    TESTPYPI = "testpypi"
    PYPI = "pypi"

    @property
    def display_name(self) -> str:
        return "TestPyPI" if self is Registry.TESTPYPI else "PyPI"

    @property
    def url(self) -> str:
        if self is Registry.TESTPYPI:
            return "https://test.pypi.org"
        return "https://pypi.org"

    @property
    def upload_url(self) -> str:
        if self is Registry.TESTPYPI:
            return "https://test.pypi.org/legacy/"
        return "https://upload.pypi.org/legacy/"

    @property
    def simple_url(self) -> str:
        if self is Registry.TESTPYPI:
            return "https://test.pypi.org/simple/"
        return "https://pypi.org/simple/"


class TokenScope(Enum):
    ACCOUNT = "account"
    PROJECT = "project"


class WorkflowMode(Enum):
    PREFLIGHT = "preflight"
    PUBLISH = "publish"


@dataclass
class VersionSource:
    """A location where a version string was found."""

    file_path: Path
    version_string: str
    label: str  # e.g. "pyproject.toml [project].version"


@dataclass
class VersionEvidence:
    """All discovered version sources and the resolved version."""

    sources: list[VersionSource]
    resolved_version: Version


@dataclass
class RegistryVersionInfo:
    """Version state from a remote registry."""

    registry: Registry
    project_name: str
    versions: list[Version]
    latest_version: Version | None

    @property
    def exists(self) -> bool:
        return len(self.versions) > 0

    def contains(self, version: Version) -> bool:
        return version in self.versions


@dataclass
class TokenMetadata:
    """Credential metadata for a registry token."""

    registry: Registry
    project_name: str
    scope: TokenScope
    needs_rotation: bool
    created_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class CredentialState:
    """Persisted credential and bootstrap state for one project+registry pair."""

    registry: Registry
    project_name: str
    token_value: str
    token_scope: TokenScope
    needs_rotation: bool = False
    created_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class BuildArtifact:
    """A single build output file."""

    path: Path
    filename: str


@dataclass
class BuildResult:
    """Result of a build operation."""

    artifacts: list[BuildArtifact]
    dist_dir: Path


@dataclass
class ReleaseTarget:
    """Fully resolved target for one release run."""

    app_dir: Path
    archive_dir: Path
    project_name: str
    module_name: str
    version: Version
    version_evidence: VersionEvidence


@dataclass
class PublishResult:
    """Outcome of a publish attempt."""

    registry: Registry
    version: Version
    success: bool
    message: str


@dataclass
class VerificationResult:
    """Outcome of post-publish verification."""

    success: bool
    message: str
    command_output: str = ""


@dataclass
class RunSummary:
    """Summary of an entire pydeli run."""

    target: ReleaseTarget
    mode: WorkflowMode
    build_result: BuildResult | None = None
    testpypi_result: PublishResult | None = None
    verification_result: VerificationResult | None = None
    pypi_result: PublishResult | None = None
