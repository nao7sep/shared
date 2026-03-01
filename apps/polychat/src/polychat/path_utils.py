"""Path mapping utilities for special prefixes (~, @).

This module provides path mapping functionality to support:
- ~ or ~/... → User home directory
- @ or @/... → App package directory (contains bundled prompts/resources)
- Native absolute paths → Used as-is
- Windows absolute paths (C:\\..., C:/..., UNC) → Supported on Windows,
  rejected on non-Windows hosts
- Relative paths without prefix → Error (to avoid ambiguity)
"""

from pathlib import Path, PureWindowsPath
import unicodedata


def get_app_root() -> Path:
    """Get app root directory.

    Returns the installed `polychat` package directory.

    Returns:
        Path to app root directory
    """
    # This file is at: polychat/path_utils.py
    # App root should be the package directory so "@/..." resolves to
    # bundled resources both in source checkouts and site-packages installs.
    return Path(__file__).resolve().parent


def has_home_path_prefix(path: str) -> bool:
    """Return True when path uses the supported home prefix forms."""
    return path == "~" or path.startswith("~/") or path.startswith("~\\")


def has_app_path_prefix(path: str) -> bool:
    """Return True when path uses the supported app-root prefix forms."""
    return path == "@" or path.startswith("@/") or path.startswith("@\\")


def is_windows_absolute_path(path: str) -> bool:
    """Return True when path is an absolute Windows path (drive or UNC)."""
    return PureWindowsPath(path).is_absolute()


def _normalize_path_input(path: str) -> str:
    """Normalize input text to NFC and reject NUL characters."""
    if "\x00" in path:
        raise ValueError("Path contains NUL character")
    return unicodedata.normalize("NFC", path)


def map_path(path: str) -> str:
    """Map path with special prefixes to absolute path.

    Supports special prefixes (with / or \\ for Windows compatibility):
    - ~/... or ~\\... → expands to user home directory
    - @/... or @\\... → expands to app root directory
    - Native absolute paths → used as-is
    - Windows absolute paths (C:\\, C:/, UNC) → accepted on Windows, rejected on non-Windows
    - Relative paths without prefix → Error

    Args:
        path: Path to map (can have ~, @, or be absolute)

    Returns:
        Absolute path string

    Raises:
        ValueError: If path is relative without special prefix, escapes boundary,
            or uses a Windows absolute path on non-Windows

    Examples:
        >>> map_path("~/chats/my-chat.json")  # Unix
        '/Users/username/chats/my-chat.json'

        >>> map_path("~\\chats\\my-chat.json")  # Windows
        'C:\\Users\\username\\chats\\my-chat.json'

        >>> map_path("@/prompts/title.txt")
        '/path/to/polychat/prompts/title.txt'

        >>> map_path("/usr/local/data/profile.json")  # Unix
        '/usr/local/data/profile.json'

        >>> map_path("C:\\Users\\data\\profile.json")  # Windows-only
        'C:\\Users\\data\\profile.json'

        >>> map_path("relative/path.json")
        ValueError: Relative paths without prefix are not supported
    """
    path = _normalize_path_input(path)

    # Handle tilde (home directory)
    # Support both ~/ and ~\ for Windows compatibility
    if has_home_path_prefix(path):
        if path == "~":
            return str(Path.home().resolve())

        home_dir = Path.home().resolve()
        suffix = path[2:]  # Everything after ~/ or ~\
        resolved = (home_dir / suffix).resolve()
        try:
            resolved.relative_to(home_dir)
        except ValueError:
            raise ValueError(f"Path escapes home directory: {path}")
        return str(resolved)

    # Handle @ (app root directory)
    # Support both @/ and @\ for Windows compatibility
    elif has_app_path_prefix(path):
        if path == "@":
            return str(get_app_root())

        app_root = get_app_root()
        suffix = path[2:]  # Everything after @/ or @\
        resolved = (app_root / suffix).resolve()
        try:
            resolved.relative_to(app_root)
        except ValueError:
            raise ValueError(f"Path escapes app directory: {path}")
        return str(resolved)

    # Absolute path - use as-is.
    # On non-Windows hosts, reject Windows absolute paths explicitly.
    if is_windows_absolute_path(path) and not Path(path).is_absolute():
        raise ValueError(
            f"Windows absolute paths are not supported on this platform: {path}"
        )

    # Works for native absolute paths on the current platform.
    elif Path(path).is_absolute():
        return str(Path(path).resolve())

    # Relative path without prefix - ERROR
    else:
        raise ValueError(
            f"Relative paths without prefix are not supported: {path}\n"
            f"Use '~/' for home directory, '@/' for app directory, "
            f"or provide an absolute path"
        )
