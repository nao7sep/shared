"""Path resolution and validation.

Rules:
- Normalize NFD -> NFC before checks.
- Reject NUL bytes.
- Accept absolute paths as-is.
- Expand ~ to user home.
- Reject pure relative paths (no base dir in v1).
- Reject Windows rooted-but-not-fully-qualified forms.
- Resolve dot segments only after path is absolute.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from .errors import PathError

_WINDOWS_ROOTED_RE = re.compile(r"^[A-Za-z]:[^/\\]|^\\[^\\]")


def resolve_path(raw: str) -> Path:
    """Resolve a user-supplied path string to an absolute Path.

    Raises PathError for invalid input.
    """
    if not raw:
        raise PathError("Path must not be empty.")

    # NFC normalization
    normalized = unicodedata.normalize("NFC", raw)

    # Reject NUL bytes
    if "\x00" in normalized:
        raise PathError("Path must not contain NUL bytes.")

    # Reject Windows rooted-but-not-fully-qualified forms
    if _WINDOWS_ROOTED_RE.match(normalized):
        raise PathError(
            f"Windows rooted-but-not-fully-qualified path is not accepted: {normalized}"
        )

    # Expand tilde
    path = Path(normalized).expanduser()

    # After expansion, must be absolute
    if not path.is_absolute():
        raise PathError(
            f"Relative paths are not accepted. Provide an absolute path or use ~: {raw}"
        )

    # Resolve dot segments now that we have an absolute path
    return path.resolve()


def validate_directory(path: Path, label: str) -> Path:
    """Ensure a resolved path is an existing directory."""
    if not path.exists():
        raise PathError(f"{label} does not exist: {path}")
    if not path.is_dir():
        raise PathError(f"{label} is not a directory: {path}")
    return path


def validate_file(path: Path, label: str) -> Path:
    """Ensure a resolved path is an existing file."""
    if not path.exists():
        raise PathError(f"{label} does not exist: {path}")
    if not path.is_file():
        raise PathError(f"{label} is not a file: {path}")
    return path


_SAFE_SEGMENT_RE = re.compile(r"[^A-Za-z0-9_.\-]")
_COLLAPSE_HYPHENS_RE = re.compile(r"-{2,}")


def sanitize_filename_segment(raw: str) -> str:
    """Sanitize a single filename segment derived from a project/package name.

    Preserves letters, digits, _, -, and .
    Converts other characters to -.
    Collapses repeated hyphens, trims outer hyphens and periods.
    Raises PathError if result is empty.
    """
    result = _SAFE_SEGMENT_RE.sub("-", raw)
    result = _COLLAPSE_HYPHENS_RE.sub("-", result)
    result = result.strip("-.")
    if not result:
        raise PathError(f"Filename segment is empty after sanitization: {raw!r}")
    return result
