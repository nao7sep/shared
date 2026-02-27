"""Profile management: loading, creation, and path mapping."""

import json
import ntpath
import os
import posixpath
import re
import sys
import unicodedata
from datetime import time as time_type
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from tk.errors import TkConfigError

_TIME_WITH_SECONDS_RE = re.compile(r"^(\d{1,2}):(\d{2}):(\d{2})$")
_TIME_WITHOUT_SECONDS_RE = re.compile(r"^(\d{1,2}):(\d{2})$")


def _normalize_path_text(path: str) -> str:
    """Normalize user path input and reject invalid path text."""
    normalized = unicodedata.normalize("NFC", path)
    if "\0" in normalized:
        raise TkConfigError("Path cannot contain NUL bytes")
    return normalized


def _is_shortcut_with_subpath(path: str, shortcut: str) -> bool:
    return path.startswith(shortcut) and len(path) > 1 and path[1] in ("/", "\\")


def _is_windows_rooted_not_fully_qualified(path: str) -> bool:
    """Return True for Windows rooted-but-not-fully-qualified forms."""
    drive, tail = ntpath.splitdrive(path)
    if drive and tail and not tail.startswith(("/", "\\")):
        return True  # Ex: C:temp
    if not drive and path.startswith("\\") and not path.startswith("\\\\"):
        return True  # Ex: \temp
    return False


def _is_absolute_path(path: str) -> bool:
    return Path(path).is_absolute() or ntpath.isabs(path)


def _resolve_dot_segments(path: str | Path) -> str:
    """Resolve dot segments without introducing CWD dependence."""
    path_text = str(path)
    if ntpath.isabs(path_text) and not Path(path_text).is_absolute():
        return ntpath.normpath(path_text)
    return posixpath.normpath(path_text)


def _runtime_app_root() -> Path:
    """Resolve runtime app root for @/ path mapping."""
    configured = os.getenv("TK_APP_ROOT")
    if configured:
        configured = _normalize_path_text(configured)
        if _is_windows_rooted_not_fully_qualified(configured):
            raise TkConfigError(
                f"Invalid TK_APP_ROOT path: {configured}. Use an absolute path."
            )
        if not _is_absolute_path(configured):
            raise TkConfigError(
                f"Invalid TK_APP_ROOT path: {configured}. Use an absolute path."
            )
        return Path(_resolve_dot_segments(configured))

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    # Source/package mode: runtime package directory.
    return Path(__file__).resolve().parent


def _normalize_shortcut_subpath(path: str) -> str:
    """Normalize shortcut subpath separators for cross-platform behavior."""
    return path[1:].lstrip("/\\").replace("\\", "/")


def _resolve_profile_path(path: str) -> Path:
    """Resolve profile path without using current working directory."""
    normalized = _normalize_path_text(path)

    if _is_windows_rooted_not_fully_qualified(normalized):
        raise TkConfigError(
            f"Invalid profile path: {path}. Windows rooted path must be fully qualified."
        )

    if normalized == "~" or _is_shortcut_with_subpath(normalized, "~"):
        mapped = Path.home() / _normalize_shortcut_subpath(normalized)
        return Path(_resolve_dot_segments(mapped))

    if normalized == "@" or _is_shortcut_with_subpath(normalized, "@"):
        mapped = _runtime_app_root() / _normalize_shortcut_subpath(normalized)
        return Path(_resolve_dot_segments(mapped))

    if _is_absolute_path(normalized):
        return Path(_resolve_dot_segments(normalized))

    raise TkConfigError(
        "Profile path must be absolute or start with '~/' or '@/'. "
        "Relative profile paths are not supported."
    )


def map_path(path: str, profile_dir: str) -> str:
    """Map relative paths with ~ or @ prefix to absolute paths.

    Args:
        path: Path to map (can start with ~, @, or be relative/absolute)
        profile_dir: Directory where the profile file is located

    Returns:
        Absolute path string

    Mapping rules:
        ~ or ~/ or ~\\ -> user home directory
        @ or @/ or @\\ -> runtime app root
        Relative paths -> relative to profile_dir
        Absolute paths -> used as-is
    """
    normalized = _normalize_path_text(path)

    if _is_windows_rooted_not_fully_qualified(normalized):
        raise TkConfigError(
            f"Invalid path: {path}. Windows rooted path must be fully qualified."
        )

    if normalized == "~":
        return str(Path.home())

    if _is_shortcut_with_subpath(normalized, "~"):
        mapped = Path.home() / _normalize_shortcut_subpath(normalized)
        return _resolve_dot_segments(mapped)

    if normalized == "@":
        return str(_runtime_app_root())

    if _is_shortcut_with_subpath(normalized, "@"):
        mapped = _runtime_app_root() / _normalize_shortcut_subpath(normalized)
        return _resolve_dot_segments(mapped)

    if _is_absolute_path(normalized):
        return _resolve_dot_segments(normalized)

    # Relative path - resolve relative to profile directory.
    mapped = Path(profile_dir) / normalized
    return _resolve_dot_segments(mapped)


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
        TkConfigError: If profile path/profile data is invalid
        json.JSONDecodeError: If JSON is malformed
    """
    profile_path = _resolve_profile_path(path)

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
    profile_path = _resolve_profile_path(path)

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
        print()
        system_timezone = "UTC"

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
