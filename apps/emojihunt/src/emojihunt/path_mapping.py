import re
import unicodedata
from pathlib import Path, PurePosixPath

from .errors import EmojihuntError

_WINDOWS_DRIVE_RELATIVE_RE = re.compile(r"^[A-Za-z]:[^/\\]")

# App root is the package directory containing this file.
_APP_ROOT: Path = Path(__file__).resolve().parent


def map_user_path(path_text: str) -> Path:
    """Map user-supplied path text to an absolute Path.

    Accepts absolute paths, ~-prefixed paths, and @-prefixed app-root-relative paths.
    Rejects pure relative paths, empty paths, paths with NUL, and
    Windows rooted-but-not-fully-qualified forms.
    CWD is never used for resolution.
    """
    normalized = _normalize_path_text(path_text)
    if _is_windows_rooted_not_qualified(normalized):
        raise EmojihuntError(
            "Windows rooted path forms like '\\temp' and 'C:temp' are not supported."
        )

    if normalized.startswith("@"):
        return _resolve_app_root_path(normalized)

    candidate = Path(_normalize_separators(normalized)).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()

    raise EmojihuntError(
        "Relative paths are not supported. Use absolute paths, '~', or '@'."
    )


def _resolve_app_root_path(normalized: str) -> Path:
    root = _APP_ROOT

    suffix = _normalize_separators(normalized[1:]).lstrip("/")
    if not suffix:
        return root

    parts = PurePosixPath(suffix).parts
    if any(part == ".." for part in parts):
        raise EmojihuntError("'@'-prefixed paths cannot escape the app root.")

    candidate = root.joinpath(*parts).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as err:
        raise EmojihuntError("'@'-prefixed paths cannot escape the app root.") from err
    return candidate


def _normalize_path_text(path_text: str) -> str:
    normalized = unicodedata.normalize("NFC", path_text.strip())
    if not normalized:
        raise EmojihuntError("Path input cannot be empty.")
    if "\0" in normalized:
        raise EmojihuntError("Path input cannot contain NUL.")
    return normalized


def _normalize_separators(path_text: str) -> str:
    return re.sub(r"[\\/]+", "/", path_text)


def _is_windows_rooted_not_qualified(path_text: str) -> bool:
    if _WINDOWS_DRIVE_RELATIVE_RE.match(path_text):
        return True
    return path_text.startswith("\\") and not path_text.startswith("\\\\")
