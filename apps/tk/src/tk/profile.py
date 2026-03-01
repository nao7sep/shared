"""Profile management: loading, creation, and path mapping."""

import json
import re
import unicodedata
from datetime import time as time_type
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from tk.errors import ConfigError
from tk.models import Profile

_TIME_WITH_SECONDS_RE = re.compile(r"^(\d{1,2}):(\d{2}):(\d{2})$")
_TIME_WITHOUT_SECONDS_RE = re.compile(r"^(\d{1,2}):(\d{2})$")
_WINDOWS_DRIVE_RELATIVE_RE = re.compile(r"^[A-Za-z]:[^/\\]")


def _normalize_path_text(path: str) -> str:
    normalized = unicodedata.normalize("NFC", path)
    if "\0" in normalized:
        raise ConfigError("Path cannot contain NUL bytes")
    return normalized


def _is_windows_rooted_not_qualified(path: str) -> bool:
    if _WINDOWS_DRIVE_RELATIVE_RE.match(path):
        return True
    return path.startswith("\\") and not path.startswith("\\\\")


def _runtime_app_root() -> Path:
    return Path(__file__).resolve().parent


def map_path(path: str, profile_dir: str | None = None) -> str:
    """Resolve a path string to an absolute path string.

    ~ or ~/...  -> user home directory
    @ or @/...  -> runtime app root (package directory)
    Absolute    -> used as-is
    Relative    -> resolved relative to profile_dir if given; error otherwise
    """
    normalized = _normalize_path_text(path)

    if _is_windows_rooted_not_qualified(normalized):
        raise ConfigError(
            f"Invalid path: {path}. Windows rooted path must be fully qualified "
            "(e.g. 'C:\\\\folder', not 'C:folder' or '\\folder')."
        )

    if normalized.startswith("@"):
        suffix = re.sub(r"[\\/]+", "/", normalized[1:]).lstrip("/")
        result = (_runtime_app_root() / suffix) if suffix else _runtime_app_root()
        return str(result.resolve())

    candidate = Path(re.sub(r"[\\/]+", "/", normalized)).expanduser()
    if candidate.is_absolute():
        return str(candidate.resolve())

    if profile_dir is not None:
        return str((Path(profile_dir) / candidate).resolve())

    raise ConfigError(
        "Relative profile paths are not supported. "
        "Use an absolute path or start with '~/' or '@/'."
    )


def parse_time(time_str: str) -> tuple[int, int, int]:
    """Parse time string in HH:MM or HH:MM:SS format.

    Args:
        time_str: Time string to parse

    Returns:
        Tuple of (hours, minutes, seconds)

    Raises:
        ConfigError: If format is invalid
    """
    match = _TIME_WITH_SECONDS_RE.match(time_str)
    if match:
        hours, minutes, seconds = match.groups()
        parsed = (int(hours), int(minutes), int(seconds))
        try:
            time_type(*parsed)
        except ValueError as e:
            raise ConfigError(
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
            raise ConfigError(
                f"Time out of range: {time_str}. Expected 00:00 to 23:59:59"
            ) from e
        return parsed

    raise ConfigError(f"Invalid time format: {time_str}. Expected HH:MM or HH:MM:SS")


def validate_profile(profile: dict[str, Any]) -> None:
    """Validate profile structure.

    Args:
        profile: Profile dictionary to validate

    Raises:
        ConfigError: If profile is invalid
    """
    required_fields = ["data_path", "output_path", "timezone", "subjective_day_start"]
    missing = [f for f in required_fields if f not in profile]

    if missing:
        raise ConfigError(f"Profile missing required fields: {', '.join(missing)}")

    # Validate time format
    try:
        parse_time(profile["subjective_day_start"])
    except ConfigError as e:
        raise ConfigError(f"Invalid subjective_day_start: {e}")

    # Validate timezone.
    if not isinstance(profile["timezone"], str) or not profile["timezone"]:
        raise ConfigError("timezone must be a non-empty string")
    try:
        ZoneInfo(profile["timezone"])
    except ZoneInfoNotFoundError as e:
        raise ConfigError(f"Invalid timezone: {profile['timezone']}") from e


def load_profile(path: str) -> Profile:
    """Load and validate profile from JSON file.

    Args:
        path: Path to profile file

    Returns:
        Profile model with absolute paths

    Raises:
        FileNotFoundError: If profile doesn't exist
        ConfigError: If profile path/profile data is invalid
        json.JSONDecodeError: If JSON is malformed
    """
    profile_path = Path(map_path(path))

    if not profile_path.exists():
        raise FileNotFoundError(
            f"Profile not found: {profile_path}\n"
            "Use 'init' command to create a profile"
        )

    with open(profile_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    validate_profile(raw)

    # Set defaults for optional sync settings (backward compatibility)
    if "auto_sync" not in raw:
        raw["auto_sync"] = True
    if "sync_on_exit" not in raw:
        raw["sync_on_exit"] = False

    # Map relative paths
    profile_dir = str(profile_path.parent)
    raw["data_path"] = map_path(raw["data_path"], profile_dir)
    raw["output_path"] = map_path(raw["output_path"], profile_dir)

    return Profile.from_dict(raw)


def create_profile(path: str) -> Profile:
    """Create new profile with defaults.

    Args:
        path: Where to save the profile

    Returns:
        Created Profile model

    Defaults:
        - timezone: system timezone
        - subjective_day_start: "04:00:00"
        - data_path: same directory as profile, "tasks.json"
        - output_path: same directory as profile, "TODO.md"
        - auto_sync: true (sync TODO.md on every data change)
        - sync_on_exit: false (sync on app exit - redundant if auto_sync is true)
    """
    profile_path = Path(map_path(path))

    # Create directory if it doesn't exist
    profile_path.parent.mkdir(parents=True, exist_ok=True)

    # Get system timezone using tzlocal
    try:
        from tzlocal import get_localzone
        tz = get_localzone()
        system_timezone = str(tz)
    except Exception as e:
        # Fallback to UTC if detection fails
        print(f"WARNING: Could not detect system timezone ({e})")
        print("Falling back to UTC. Edit the profile JSON to set your timezone manually.")
        system_timezone = "UTC"

    raw = {
        "data_path": "./tasks.json",
        "output_path": "./TODO.md",
        "timezone": system_timezone,
        "subjective_day_start": "04:00:00",
        "auto_sync": True,
        "sync_on_exit": False
    }

    # Save profile
    with open(profile_path, "w", encoding="utf-8") as f:
        json.dump(raw, f, indent=2, ensure_ascii=False)

    # Return with mapped paths
    profile_dir = str(profile_path.parent)
    raw["data_path"] = map_path(raw["data_path"], profile_dir)
    raw["output_path"] = map_path(raw["output_path"], profile_dir)

    return Profile.from_dict(raw)
