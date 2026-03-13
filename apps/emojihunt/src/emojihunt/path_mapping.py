"""Path mapping utilities.

Compliant with the shared path-mapping-and-filename-sanitization specification.
Supports ~, @, and absolute paths. Never depends on the current working directory.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from .errors import PathMappingError

_WINDOWS_DRIVE_RELATIVE_RE = re.compile(r"^[A-Za-z]:[^/\\]")


def map_path(
    raw: str,
    *,
    app_root_abs: Path,
    base_dir: Path | None = None,
) -> Path:
    """Map a user-provided path string to an absolute resolved Path.

    Resolution rules (applied in order):
    1. Normalize NFD -> NFC.
    2. Reject NUL chars.
    3. Reject Windows rooted-not-qualified forms (\\name, C:name).
    4. If starts with ~, expand home dir.
    5. If starts with @, map to app_root_abs.
    6. If absolute, accept as-is.
    7. If relative + base_dir given, join onto base_dir.
    8. If relative + no base_dir, raise PathMappingError.
    9. Resolve dot segments via Path.resolve(strict=False).
    """
    if not app_root_abs.is_absolute():
        raise PathMappingError("app_root_abs must be an absolute path.")

    normalized = unicodedata.normalize("NFC", raw)
    if "\0" in normalized:
        raise PathMappingError("Path contains NUL (\\0) character.")
    if _is_windows_rooted_not_fully_qualified(normalized):
        raise PathMappingError(
            "Unsupported Windows rooted-not-qualified path form "
            "(e.g. \\name or C:name)."
        )

    mapped = _map_special_prefixes(normalized, app_root_abs)

    if not mapped.is_absolute():
        if base_dir is None:
            raise PathMappingError(
                "Relative path requires an explicit base directory. "
                "Use ~ (home), @ (app root), or an absolute path."
            )
        mapped = base_dir / mapped

    return mapped.resolve()


def _map_special_prefixes(path_text: str, app_root_abs: Path) -> Path:
    if path_text.startswith("~"):
        normalized_home = re.sub(r"[\\/]+", "/", path_text)
        return Path(normalized_home).expanduser()
    if path_text.startswith("@"):
        return _map_app_root_path(path_text, app_root_abs)
    normalized_slashes = re.sub(r"[\\/]+", "/", path_text)
    return Path(normalized_slashes)


def _map_app_root_path(path_text: str, app_root_abs: Path) -> Path:
    remainder = path_text[1:]  # strip leading @
    if not remainder:
        return app_root_abs
    remainder = remainder.lstrip("/\\")
    if not remainder:
        return app_root_abs
    segments = [s for s in re.split(r"[\\/]+", remainder) if s]
    return app_root_abs.joinpath(*segments)


def _is_windows_rooted_not_fully_qualified(path_text: str) -> bool:
    if path_text.startswith("\\") and not path_text.startswith("\\\\"):
        return True
    return _WINDOWS_DRIVE_RELATIVE_RE.match(path_text) is not None
