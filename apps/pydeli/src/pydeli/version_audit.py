"""Version source discovery, extraction, equality checks, and PEP 440 parsing.

Reads version values from:
- pyproject.toml [project].version
- src/<module>/__init__.py or <module>/__init__.py (__version__ = "...")
- src/<module>/__main__.py or <module>/__main__.py (__version__ = "...")

All discovered values must be exactly equal. pydeli never edits source files.
"""

from __future__ import annotations

import re
from pathlib import Path

from packaging.version import InvalidVersion, Version

from .errors import VersionError
from .models import VersionEvidence, VersionSource

_VERSION_ASSIGNMENT_RE = re.compile(
    r"""^__version__\s*=\s*(['"])(.*?)\1""", re.MULTILINE
)


def _extract_pyproject_version(app_dir: Path) -> VersionSource | None:
    """Extract version from pyproject.toml [project].version."""
    pyproject = app_dir / "pyproject.toml"
    if not pyproject.is_file():
        return None

    try:
        import tomllib

        with open(pyproject, "rb") as f:
            data = tomllib.load(f)

        version_str = data.get("project", {}).get("version")
        if version_str is None:
            return None
        return VersionSource(
            file_path=pyproject,
            version_string=str(version_str),
            label="pyproject.toml [project].version",
        )
    except Exception as e:
        raise VersionError(f"Failed to parse {pyproject}: {e}") from e


def _extract_python_file_version(path: Path, label: str) -> VersionSource | None:
    """Extract __version__ = "..." from a Python source file."""
    if not path.is_file():
        return None

    try:
        content = path.read_text(encoding="utf-8")
    except OSError as e:
        raise VersionError(f"Failed to read {path}: {e}") from e

    match = _VERSION_ASSIGNMENT_RE.search(content)
    if match is None:
        return None
    return VersionSource(
        file_path=path,
        version_string=match.group(2),
        label=label,
    )


def _discover_module_name(app_dir: Path) -> str | None:
    """Find the Python module name by looking for __init__.py in standard locations."""
    # Check src/<name>/__init__.py
    src_dir = app_dir / "src"
    if src_dir.is_dir():
        for child in sorted(src_dir.iterdir()):
            if child.is_dir() and (child / "__init__.py").is_file():
                return child.name

    # Check <name>/__init__.py (flat layout)
    for child in sorted(app_dir.iterdir()):
        if (
            child.is_dir()
            and child.name != "tests"
            and not child.name.startswith(".")
            and (child / "__init__.py").is_file()
        ):
            return child.name

    return None


def discover_module_root(app_dir: Path, module_name: str) -> Path | None:
    """Return the module root directory (containing __init__.py)."""
    # src layout first
    src_path = app_dir / "src" / module_name
    if src_path.is_dir() and (src_path / "__init__.py").is_file():
        return src_path

    # flat layout
    flat_path = app_dir / module_name
    if flat_path.is_dir() and (flat_path / "__init__.py").is_file():
        return flat_path

    return None


def collect_version_sources(app_dir: Path) -> list[VersionSource]:
    """Discover all version sources from the target app directory."""
    sources: list[VersionSource] = []

    # pyproject.toml
    pyproject_src = _extract_pyproject_version(app_dir)
    if pyproject_src is not None:
        sources.append(pyproject_src)

    # Discover module name
    module_name = _discover_module_name(app_dir)
    if module_name is None:
        return sources

    module_root = discover_module_root(app_dir, module_name)
    if module_root is None:
        return sources

    # __init__.py
    init_src = _extract_python_file_version(
        module_root / "__init__.py",
        f"{module_name}/__init__.py __version__",
    )
    if init_src is not None:
        sources.append(init_src)

    # __main__.py
    main_src = _extract_python_file_version(
        module_root / "__main__.py",
        f"{module_name}/__main__.py __version__",
    )
    if main_src is not None:
        sources.append(main_src)

    return sources


def audit_versions(app_dir: Path) -> VersionEvidence:
    """Collect and validate all version sources.

    Requires at least one source. All sources must contain exactly the same
    version string, and that string must be valid PEP 440.
    """
    sources = collect_version_sources(app_dir)
    if not sources:
        raise VersionError(
            f"No version sources found in {app_dir}. "
            "Expected at least pyproject.toml [project].version or __version__ in a Python module."
        )

    # All raw strings must be identical
    unique_strings = {s.version_string for s in sources}
    if len(unique_strings) > 1:
        details = "\n".join(f"  {s.label}: {s.version_string}" for s in sources)
        raise VersionError(
            f"Version mismatch across sources:\n{details}\n"
            "All version strings must be exactly equal."
        )

    version_string = sources[0].version_string
    try:
        version = Version(version_string)
    except InvalidVersion as e:
        raise VersionError(
            f"Version string {version_string!r} is not valid PEP 440: {e}"
        ) from e

    return VersionEvidence(sources=sources, resolved_version=version)
