"""CLI path mapping helpers."""

from typing import Optional

from .path_mapping import map_path


def map_cli_path(path_value: Optional[str], arg_name: str) -> Optional[str]:
    """Map a CLI path argument using path mapping rules."""
    if path_value is None:
        return None

    try:
        return map_path(path_value)
    except ValueError as e:
        raise ValueError(f"Invalid {arg_name} path: {e}")
