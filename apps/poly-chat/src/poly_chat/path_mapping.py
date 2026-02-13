"""Path mapping utilities for special prefixes (~, @).

This module provides path mapping functionality to support:
- ~ or ~/... → User home directory
- @ or @/... → App root directory (project directory containing pyproject.toml)
- Absolute paths → Used as-is
- Relative paths without prefix → Error (to avoid ambiguity)
"""

from pathlib import Path


def get_app_root() -> Path:
    """Get app root directory.

    Returns the directory containing pyproject.toml.

    Returns:
        Path to app root directory
    """
    # Find pyproject.toml directory by going up from this file's location
    # This file is at: src/poly_chat/path_mapping.py
    # App root is 3 levels up
    return Path(__file__).parent.parent.parent


def map_path(path: str) -> str:
    """Map path with special prefixes to absolute path.

    Supports special prefixes:
    - ~/... → expands to user home directory
    - @/... → expands to app root directory
    - Absolute paths → used as-is
    - Relative paths without prefix → Error

    Args:
        path: Path to map (can have ~, @, or be absolute)

    Returns:
        Absolute path string

    Raises:
        ValueError: If path is relative without special prefix, or escapes boundary

    Examples:
        >>> map_path("~/chats/my-chat.json")
        '/Users/username/chats/my-chat.json'

        >>> map_path("@/prompts/title.txt")
        '/path/to/poly-chat/prompts/title.txt'

        >>> map_path("/usr/local/data/profile.json")
        '/usr/local/data/profile.json'

        >>> map_path("relative/path.json")
        ValueError: Relative paths without prefix are not supported
    """
    # Handle tilde (home directory)
    if path.startswith("~/"):
        home_dir = Path.home().resolve()
        resolved = (home_dir / path[2:]).resolve()
        try:
            resolved.relative_to(home_dir)
        except ValueError:
            raise ValueError(f"Path escapes home directory: {path}")
        return str(resolved)
    elif path == "~":
        return str(Path.home().resolve())

    # Handle @ (app root directory)
    elif path.startswith("@/"):
        app_root = get_app_root()
        resolved = (app_root / path[2:]).resolve()
        app_root_resolved = app_root.resolve()
        try:
            resolved.relative_to(app_root_resolved)
        except ValueError:
            raise ValueError(f"Path escapes app directory: {path}")
        return str(resolved)
    elif path == "@":
        return str(get_app_root())

    # Absolute path - use as-is
    elif Path(path).is_absolute():
        return str(Path(path).resolve())

    # Relative path without prefix - ERROR
    else:
        raise ValueError(
            f"Relative paths without prefix are not supported: {path}\n"
            f"Use '~/' for home directory, '@/' for app directory, "
            f"or provide an absolute path"
        )
