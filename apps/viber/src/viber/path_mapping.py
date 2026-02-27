"""Path mapping and filename sanitization utilities.

Compliant with the shared path-mapping-and-filename-sanitization specification.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from .errors import FilenameSanitizationError, PathMappingError

_WINDOWS_DRIVE_RELATIVE_RE = re.compile(r"^[A-Za-z]:[^/\\]")

# Characters allowed in slugify base: Unicode letters, digits, _, -, .
# Everything else is replaced with -.
_SLUGIFY_KEEP_RE = re.compile(r"[^\w\-.]", flags=re.UNICODE)
_SLUGIFY_COLLAPSE_RE = re.compile(r"-+")


def map_path(
    raw: str,
    *,
    app_root_abs: Path,
    base_dir: Path | None = None,
) -> Path:
    """Map a user-provided path string to an absolute resolved Path.

    Resolution rules (applied in order):
    1. Normalize NFD → NFC.
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


def slugify(segment: str) -> str:
    """Apply slugify mode to a single filename segment.

    - Reject path-like input that includes directory separators.
    - Lowercase.
    - Split into base and extension at last '.' (if present and not leading).
    - In base and extension: replace non-letter/digit/underscore/hyphen/dot chars with -.
    - Collapse runs of - to single -.
    - Strip leading/trailing - and . from base only.
    - Reattach lowercased extension.
    - Raise FilenameSanitizationError if result is empty.
    """
    segment = segment.lower()
    if "/" in segment or "\\" in segment:
        raise FilenameSanitizationError(segment)

    # Split extension
    dot_pos = segment.rfind(".")
    if dot_pos > 0:
        base_raw = segment[:dot_pos]
        ext_raw = segment[dot_pos + 1:]
    else:
        base_raw = segment
        ext_raw = None

    base = _slugify_component(base_raw, strip_edges=True)
    if not base:
        raise FilenameSanitizationError(segment)

    if ext_raw is None:
        return base
    ext = _slugify_component(ext_raw, strip_edges=False)
    if not ext:
        return base

    return f"{base}.{ext}"


def _map_special_prefixes(path_text: str, app_root_abs: Path) -> Path:
    if path_text.startswith("~"):
        # Normalize slash styles before expanduser so "~\\..." is handled like "~/...".
        normalized_home = re.sub(r"[\\/]+", "/", path_text)
        return Path(normalized_home).expanduser()
    if path_text.startswith("@"):
        return _map_app_root_path(path_text, app_root_abs)
    # Normalize slash styles and repeated separators
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
    # \name (not \\unc)
    if path_text.startswith("\\") and not path_text.startswith("\\\\"):
        return True
    # C:name (drive-relative, not C:\name or C:/name)
    return _WINDOWS_DRIVE_RELATIVE_RE.match(path_text) is not None


def _slugify_component(text: str, *, strip_edges: bool) -> str:
    text = _SLUGIFY_KEEP_RE.sub("-", text)
    text = _SLUGIFY_COLLAPSE_RE.sub("-", text)
    if strip_edges:
        text = text.strip("-.")
    return text
