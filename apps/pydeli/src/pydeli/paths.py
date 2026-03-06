"""Path resolution and validation.

Conforms to the shared path-mapping-and-filename-sanitization spec.

Resolution rules (in check order):
1. NFC-normalize input.
2. Reject NUL bytes.
3. Reject Windows rooted-but-not-fully-qualified forms.
4. Expand ~ to user home.
5. Expand @ to the pydeli package root (module-level constant, never CWD).
6. Accept fully-absolute paths as-is.
7. Pure relative paths require an explicit base_dir; rejected otherwise.
8. Resolve dot segments with os.path.normpath only after the path is absolute
   (no CWD involvement — normpath works on the string, not the filesystem).

CWD is NEVER used at any step. Path.resolve() is intentionally avoided in
favour of os.path.normpath() to prevent any implicit CWD fallback.
"""

from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path, PurePosixPath

from .errors import PathError

# The distributed app root for @-prefix expansion: the pydeli package directory.
# Computed once at import time from this file's own location.
_APP_ROOT: Path = Path(__file__).resolve().parent

_WINDOWS_ROOTED_RE = re.compile(r"^[A-Za-z]:[^/\\]|^\\[^\\]")


def _normalize_separators(text: str) -> str:
    """Collapse any mix of / and \\ into /."""
    return re.sub(r"[\\/]+", "/", text)


def _resolve_at_path(suffix: str) -> Path:
    """Map an @-relative suffix onto _APP_ROOT.

    Raises PathError if the suffix contains .. (escape attempt).
    """
    if not suffix:
        return _APP_ROOT

    parts = PurePosixPath(suffix).parts
    if any(part == ".." for part in parts):
        raise PathError("@ paths cannot contain '..' (cannot escape app root).")

    candidate = Path(os.path.normpath(os.path.join(str(_APP_ROOT), *parts)))

    # Verify the resolved path stays inside _APP_ROOT
    try:
        candidate.relative_to(_APP_ROOT)
    except ValueError as exc:
        raise PathError("@ path escapes the app root.") from exc

    return candidate


def resolve_path(
    raw: str,
    *,
    base_dir: Path | None = None,
) -> Path:
    """Resolve a user-supplied path string to an absolute, normalized Path.

    Prefixes:
    - ``~``  → user home directory
    - ``@``  → pydeli package root (_APP_ROOT, never CWD)
    - absolute path → accepted as-is
    - pure relative → requires explicit ``base_dir`` (never CWD)

    Raises PathError for invalid or ambiguous input.
    """
    if not raw:
        raise PathError("Path must not be empty.")

    # NFC normalization (NFD → NFC)
    normalized = unicodedata.normalize("NFC", raw)

    # Reject NUL bytes
    if "\x00" in normalized:
        raise PathError("Path must not contain NUL bytes.")

    # Reject Windows rooted-but-not-fully-qualified forms
    if _WINDOWS_ROOTED_RE.match(normalized):
        raise PathError(
            f"Windows rooted-but-not-fully-qualified path is not accepted: {normalized}"
        )

    # --- Map to an absolute string without touching the filesystem or CWD ---

    norm_slashes = _normalize_separators(normalized)

    if norm_slashes.startswith("~"):
        abs_str = os.path.expanduser(norm_slashes)

    elif norm_slashes.startswith("@"):
        suffix = norm_slashes[1:].lstrip("/")
        return _resolve_at_path(suffix)

    elif os.path.isabs(norm_slashes):
        abs_str = norm_slashes

    else:
        # Pure relative path — requires explicit base_dir, never CWD
        if base_dir is None:
            raise PathError(
                "Relative paths are not accepted without an explicit base directory. "
                "Provide an absolute path, use ~, or use @."
            )
        if not base_dir.is_absolute():
            raise PathError(f"base_dir must be absolute, got: {base_dir}")
        abs_str = os.path.join(str(base_dir), norm_slashes)

    # Resolve dot segments using normpath (string-only, no CWD, no filesystem access)
    result = Path(os.path.normpath(abs_str))

    # Final safety check: must be absolute
    if not result.is_absolute():
        raise PathError(f"Path did not resolve to an absolute path: {raw!r}")

    return result


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
