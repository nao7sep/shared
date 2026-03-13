from __future__ import annotations

import re
import tomllib
from pathlib import Path

from packaging.version import InvalidVersion, Version

from .errors import AuditError
from .models import VersionSource

VERSION_PATTERN = re.compile(r'^__version__\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)

VERSION_FILE_CANDIDATES = ("__init__.py", "__main__.py")


def audit_versions(app_dir: Path) -> tuple[Version, list[VersionSource]]:
    """Scan the app directory for version strings and verify consistency.

    Returns the unified version and the list of discovered sources.
    Raises AuditError if versions are inconsistent or none are found.
    Prints a warning if only one source is found.
    """
    sources = _collect_version_sources(app_dir)

    if not sources:
        raise AuditError(
            "No version strings found. Expected a version in pyproject.toml "
            "and __version__ in __init__.py or __main__.py."
        )

    unique_versions = {s.version_string for s in sources}
    if len(unique_versions) > 1:
        lines = ["Version mismatch detected:"]
        max_label_len = max(len(str(s.file_path)) for s in sources) + 1
        for source in sources:
            label = f"{source.file_path}:"
            lines.append(f"  {label:<{max_label_len}}  {source.version_string}")
        raise AuditError("\n".join(lines))

    version_string = sources[0].version_string
    try:
        version = Version(version_string)
    except InvalidVersion as exc:
        raise AuditError(
            f"Invalid version string: {version_string} (not PEP 440 compliant)"
        ) from exc

    if len(sources) == 1:
        print(
            f"WARNING: Version found in only one source ({sources[0].file_path}). "
            "Consider adding __version__ to __init__.py or __main__.py for consistency."
        )

    return version, sources


def _collect_version_sources(app_dir: Path) -> list[VersionSource]:
    """Find all version strings in pyproject.toml and Python source files."""
    sources: list[VersionSource] = []

    pyproject_version = _read_pyproject_version(app_dir)
    if pyproject_version is not None:
        sources.append(pyproject_version)

    package_name = _read_package_name(app_dir)
    if package_name is None:
        return sources

    module_name = package_name.replace("-", "_")

    for candidate in VERSION_FILE_CANDIDATES:
        source = _read_python_version(app_dir, module_name, candidate)
        if source is not None:
            sources.append(source)

    return sources


def _read_pyproject_version(app_dir: Path) -> VersionSource | None:
    """Extract version from pyproject.toml [project].version."""
    pyproject_path = app_dir / "pyproject.toml"
    if not pyproject_path.exists():
        return None

    try:
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
    except (tomllib.TOMLDecodeError, OSError) as exc:
        raise AuditError(f"Failed to parse {pyproject_path}: {exc}") from exc

    project = data.get("project", {})
    version = project.get("version")
    if not isinstance(version, str) or not version:
        return None

    return VersionSource(file_path=pyproject_path, version_string=version)


def _read_package_name(app_dir: Path) -> str | None:
    """Extract the package name from pyproject.toml [project].name."""
    pyproject_path = app_dir / "pyproject.toml"
    if not pyproject_path.exists():
        return None

    try:
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
    except (tomllib.TOMLDecodeError, OSError):
        return None

    project = data.get("project", {})
    name = project.get("name")
    if isinstance(name, str) and name:
        return name
    return None


def _read_python_version(
    app_dir: Path, module_name: str, filename: str
) -> VersionSource | None:
    """Extract __version__ from a Python source file.

    Checks both src/<module>/<filename> and <module>/<filename> layouts.
    """
    candidates = [
        app_dir / "src" / module_name / filename,
        app_dir / module_name / filename,
    ]

    for file_path in candidates:
        if not file_path.exists():
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
        except OSError:
            continue

        match = VERSION_PATTERN.search(content)
        if match:
            return VersionSource(file_path=file_path, version_string=match.group(1))

    return None
