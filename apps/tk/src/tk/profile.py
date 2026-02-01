"""Profile management: loading, creation, and path mapping."""

import json
from pathlib import Path
from typing import Any
from datetime import datetime
import re


def map_path(path: str, profile_dir: str) -> str:
    """Map relative paths with ~ or @ prefix to absolute paths.

    Args:
        path: Path to map (can start with ~, @, or be absolute)
        profile_dir: Directory where the profile file is located

    Returns:
        Absolute path string

    Mapping rules:
        ~ -> user home directory
        @ -> app directory (where pyproject.toml is located)
        Otherwise: treat as absolute path
    """
    if path.startswith("~"):
        return str(Path.home() / path[2:])  # Skip "~/"
    elif path.startswith("@"):
        # App directory is the root of the tk package (where pyproject.toml is)
        app_dir = Path(__file__).parent.parent.parent
        return str(app_dir / path[2:])  # Skip "@/"
    else:
        return path


def parse_time(time_str: str) -> tuple[int, int, int]:
    """Parse time string in HH:MM or HH:MM:SS format.

    Args:
        time_str: Time string to parse

    Returns:
        Tuple of (hours, minutes, seconds)

    Raises:
        ValueError: If format is invalid
    """
    # Support both HH:MM and HH:MM:SS
    pattern_with_seconds = r"^(\d{1,2}):(\d{2}):(\d{2})$"
    pattern_without_seconds = r"^(\d{1,2}):(\d{2})$"

    match = re.match(pattern_with_seconds, time_str)
    if match:
        hours, minutes, seconds = match.groups()
        return int(hours), int(minutes), int(seconds)

    match = re.match(pattern_without_seconds, time_str)
    if match:
        hours, minutes = match.groups()
        return int(hours), int(minutes), 0

    raise ValueError(f"Invalid time format: {time_str}. Expected HH:MM or HH:MM:SS")


def validate_profile(profile: dict[str, Any]) -> None:
    """Validate profile structure.

    Args:
        profile: Profile dictionary to validate

    Raises:
        ValueError: If profile is invalid
    """
    required_fields = ["data_path", "output_path", "timezone", "subjective_day_start"]
    missing = [f for f in required_fields if f not in profile]

    if missing:
        raise ValueError(f"Profile missing required fields: {', '.join(missing)}")

    # Validate time format
    try:
        parse_time(profile["subjective_day_start"])
    except ValueError as e:
        raise ValueError(f"Invalid subjective_day_start: {e}")

    # Validate timezone (basic check - full validation happens in zoneinfo)
    if not isinstance(profile["timezone"], str) or not profile["timezone"]:
        raise ValueError("timezone must be a non-empty string")


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
            f"Use 'new' command to create a profile"
        )

    with open(profile_path, "r") as f:
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

    # Get system timezone
    try:
        # Method 1: Try to read from /etc/localtime symlink (macOS/Linux)
        import os
        localtime_path = Path("/etc/localtime")
        if localtime_path.exists() and localtime_path.is_symlink():
            # /etc/localtime -> /var/db/timezone/zoneinfo/Asia/Tokyo
            target = os.readlink(localtime_path)
            if "zoneinfo/" in target:
                system_timezone = target.split("zoneinfo/")[-1]
            else:
                raise ValueError("Could not parse timezone from symlink")
        else:
            # Method 2: Try datetime.now().astimezone().tzname()
            from zoneinfo import ZoneInfo
            local_tz = datetime.now().astimezone().tzinfo

            # Try to get the key attribute (Python 3.9+)
            if hasattr(local_tz, 'key'):
                system_timezone = local_tz.key
            else:
                # Fallback: use tzname which returns abbreviation like "JST"
                # We'll map common ones, otherwise default to UTC
                tzname = datetime.now().astimezone().tzname()
                timezone_map = {
                    "JST": "Asia/Tokyo",
                    "EST": "America/New_York",
                    "PST": "America/Los_Angeles",
                    "GMT": "Europe/London",
                }
                system_timezone = timezone_map.get(tzname, "UTC")
    except Exception:
        system_timezone = "UTC"

    profile_dir = str(profile_path.parent)

    profile = {
        "data_path": str(profile_path.parent / "tasks.json"),
        "output_path": str(profile_path.parent / "TODO.md"),
        "timezone": system_timezone,
        "subjective_day_start": "04:00:00",
        "auto_sync": True,
        "sync_on_exit": False
    }

    # Save profile
    with open(profile_path, "w") as f:
        json.dump(profile, f, indent=2)

    return profile
