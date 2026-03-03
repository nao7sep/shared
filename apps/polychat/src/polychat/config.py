"""Per-user application configuration (~/.polychat/config.json)."""

from __future__ import annotations

import functools
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

CONFIG_PATH = Path.home() / ".polychat" / "config.json"

# Default values — single source of truth for both the generated file and runtime defaults.
DEFAULT_MACOS_SOUND: str = "Tink"
DEFAULT_WINDOWS_SOUND: str = "SystemAsterisk"
DEFAULT_LINUX_SOUND: None = None
DEFAULT_VOLUME: float = 1.0
DEFAULT_USER_INPUT_COLOR: str = "ansibrightgreen"
DEFAULT_COST_LINE_COLOR: str = "ansibrightyellow"

_DEFAULT_CONFIG = {
    "notifications": {
        "sound": True,
        "macos_sound": DEFAULT_MACOS_SOUND,
        "windows_sound": DEFAULT_WINDOWS_SOUND,
        "linux_sound": DEFAULT_LINUX_SOUND,
        "volume": DEFAULT_VOLUME,
    },
    "display": {
        "user_input_color": DEFAULT_USER_INPUT_COLOR,
        "cost_line_color": DEFAULT_COST_LINE_COLOR,
    },
}


class ConfigError(Exception):
    """Raised when config.json exists but cannot be parsed."""


@dataclass
class NotificationsConfig:
    sound: bool = True
    macos_sound: Optional[str] = DEFAULT_MACOS_SOUND
    windows_sound: Optional[str] = DEFAULT_WINDOWS_SOUND
    linux_sound: Optional[str] = DEFAULT_LINUX_SOUND
    volume: float = DEFAULT_VOLUME


@dataclass
class DisplayConfig:
    user_input_color: str = DEFAULT_USER_INPUT_COLOR
    cost_line_color: str = DEFAULT_COST_LINE_COLOR


@dataclass
class AppConfig:
    notifications: NotificationsConfig = field(default_factory=NotificationsConfig)
    display: DisplayConfig = field(default_factory=DisplayConfig)


@functools.lru_cache(maxsize=1)
def load_config() -> AppConfig:
    """Load config from ~/.polychat/config.json, creating it with defaults if absent.

    Raises:
        ConfigError: If the file exists but cannot be parsed.
    """
    if not CONFIG_PATH.exists():
        try:
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            CONFIG_PATH.write_text(
                json.dumps(_DEFAULT_CONFIG, indent=2) + "\n",
                encoding="utf-8",
            )
        except Exception:
            pass
        return AppConfig()

    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ConfigError(
            f"{CONFIG_PATH} is not valid: {exc}\n"
            f"To reset it to defaults, delete the file and restart PolyChat."
        ) from exc

    notif_data = data.get("notifications", {}) if isinstance(data, dict) else {}
    display_data = data.get("display", {}) if isinstance(data, dict) else {}

    notifications = NotificationsConfig(
        sound=notif_data.get("sound", True),
        macos_sound=notif_data.get("macos_sound", DEFAULT_MACOS_SOUND),
        windows_sound=notif_data.get("windows_sound", DEFAULT_WINDOWS_SOUND),
        linux_sound=notif_data.get("linux_sound", DEFAULT_LINUX_SOUND),
        volume=notif_data.get("volume", DEFAULT_VOLUME),
    )

    display = DisplayConfig(
        user_input_color=display_data.get("user_input_color", DEFAULT_USER_INPUT_COLOR),
        cost_line_color=display_data.get("cost_line_color", DEFAULT_COST_LINE_COLOR),
    )

    return AppConfig(notifications=notifications, display=display)
