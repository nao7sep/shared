"""Profile management: loading, creation, and path mapping."""

import json
import re
from datetime import time as time_type
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from tk.errors import TkConfigError

_APP_DIR = Path(__file__).resolve().parents[2]
_TIME_WITH_SECONDS_RE = re.compile(r"^(\d{1,2}):(\d{2}):(\d{2})$")
_TIME_WITHOUT_SECONDS_RE = re.compile(r"^(\d{1,2}):(\d{2})$")


def _normalize_shortcut_subpath(path: str) -> str:
    """Normalize shortcut subpath separators for cross-platform behavior."""
    return path[2:].replace("\\", "/")


def map_path(path: str, profile_dir: str) -> str:
    """Map relative paths with ~ or @ prefix to absolute paths.

    Args:
        path: Path to map (can start with ~, @, or be relative/absolute)
        profile_dir: Directory where the profile file is located

    Returns:
        Absolute path string

    Mapping rules:
        ~ or ~/ or ~\\ -> user home directory
        @ or @/ or @\\ -> app directory (where pyproject.toml is located)
        Relative paths -> relative to profile_dir
        Absolute paths -> used as-is
    """
    if path.startswith("~/") or path.startswith("~\\"):
        return str(Path.home() / _normalize_shortcut_subpath(path))
    elif path == "~":
        return str(Path.home())
    elif path.startswith("@/") or path.startswith("@\\"):
        # App directory is the project root (where pyproject.toml is).
        return str(_APP_DIR / _normalize_shortcut_subpath(path))
    elif path == "@":
        return str(_APP_DIR)
    elif Path(path).is_absolute():
        return path
    else:
        # Relative path - resolve relative to profile directory
        return str(Path(profile_dir) / path)


def parse_time(time_str: str) -> tuple[int, int, int]:
    """Parse time string in HH:MM or HH:MM:SS format.

    Args:
        time_str: Time string to parse

    Returns:
        Tuple of (hours, minutes, seconds)

    Raises:
        TkConfigError: If format is invalid
    """
    match = _TIME_WITH_SECONDS_RE.match(time_str)
    if match:
        hours, minutes, seconds = match.groups()
        parsed = (int(hours), int(minutes), int(seconds))
        try:
            time_type(*parsed)
        except ValueError as e:
            raise TkConfigError(
                f"Time out of range: {time_str}. Expected 00:00 to 23:59:59"
            ) from e
        return parsed

    match = _TIME_WITHOUT_SECONDS_RE.match(time_str)
    if match:
        hours, minutes = match.groups()
        parsed = (int(hours), int(minutes), 0)
        try:
            time_type(*parsed)
        except ValueError as e:
            raise TkConfigError(
                f"Time out of range: {time_str}. Expected 00:00 to 23:59:59"
            ) from e
        return parsed

    raise TkConfigError(f"Invalid time format: {time_str}. Expected HH:MM or HH:MM:SS")


def validate_profile(profile: dict[str, Any]) -> None:
    """Validate profile structure.

    Args:
        profile: Profile dictionary to validate

    Raises:
        TkConfigError: If profile is invalid
    """
    required_fields = ["data_path", "output_path", "timezone", "subjective_day_start"]
    missing = [f for f in required_fields if f not in profile]

    if missing:
        raise TkConfigError(f"Profile missing required fields: {', '.join(missing)}")

    # Validate time format
    try:
        parse_time(profile["subjective_day_start"])
    except TkConfigError as e:
        raise TkConfigError(f"Invalid subjective_day_start: {e}")

    # Validate timezone.
    if not isinstance(profile["timezone"], str) or not profile["timezone"]:
        raise TkConfigError("timezone must be a non-empty string")
    try:
        ZoneInfo(profile["timezone"])
    except ZoneInfoNotFoundError as e:
        raise TkConfigError(f"Invalid timezone: {profile['timezone']}") from e


def load_profile(path: str) -> dict[str, Any]:
    """Load and validate profile from JSON file.

    Args:
        path: Path to profile file

    Returns:
        Profile dictionary with absolute paths

    Raises:
        FileNotFoundError: If profile doesn't exist
        ValueError: If profile is invalid
        json.JSONDecodeError: If JSON is malformed
    """
    profile_path = Path(path).expanduser().resolve()

    if not profile_path.exists():
        raise FileNotFoundError(
            f"Profile not found: {profile_path}\n"
            "Use 'init' command to create a profile"
        )

    with open(profile_path, "r", encoding="utf-8") as f:
        profile = json.load(f)

    validate_profile(profile)

    # Set defaults for optional sync settings (backward compatibility)
    if "auto_sync" not in profile:
        profile["auto_sync"] = True
    if "sync_on_exit" not in profile:
        profile["sync_on_exit"] = False

    # Map relative paths
    profile_dir = str(profile_path.parent)
    profile["data_path"] = map_path(profile["data_path"], profile_dir)
    profile["output_path"] = map_path(profile["output_path"], profile_dir)

    return profile


def create_profile(path: str) -> dict[str, Any]:
    """Create new profile with defaults.

    Args:
        path: Where to save the profile

    Returns:
        Created profile dictionary

    Defaults:
        - timezone: system timezone
        - subjective_day_start: "04:00:00"
        - data_path: same directory as profile, "tasks.json"
        - output_path: same directory as profile, "TODO.md"
        - auto_sync: true (sync TODO.md on every data change)
        - sync_on_exit: false (sync on app exit - redundant if auto_sync is true)
    """
    profile_path = Path(path).expanduser().resolve()

    # Create directory if it doesn't exist
    profile_path.parent.mkdir(parents=True, exist_ok=True)

    # Get system timezone using tzlocal
    try:
        from tzlocal import get_localzone
        tz = get_localzone()
        system_timezone = str(tz)
    except Exception as e:
        # Fallback to UTC if detection fails
        print(f"Warning: Could not detect system timezone ({e})")
        print("Falling back to UTC. Edit the profile JSON to set your timezone manually.")
        system_timezone = "UTC"

    profile_dir = str(profile_path.parent)

    profile = {
        "data_path": "./tasks.json",
        "output_path": "./TODO.md",
        "timezone": system_timezone,
        "subjective_day_start": "04:00:00",
        "auto_sync": True,
        "sync_on_exit": False
    }

    # Save profile
    with open(profile_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)

    return profile
