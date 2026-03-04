"""Notification sound config resolution and validation."""

from __future__ import annotations

import os
import re
from pathlib import Path

from ...domain.config import AppConfig
from ...path_utils import (
    has_app_path_prefix,
    has_home_path_prefix,
    is_windows_absolute_path,
    map_path,
)
from .contracts import ResolvedNotificationSound
from .platform_lookup import resolve_system_sound_path

DEFAULT_SOUND_NOTIFICATIONS_ENABLED = True
DEFAULT_NOTIFICATION_VOLUME = 1.0

_DEFAULT_NOTIFICATION_SOUND_TOKENS = {
    "darwin": ("Tink", "Glass", "Ping"),
    "win32": ("SystemAsterisk", "SystemNotification", "SystemExclamation"),
    "linux": ("dialog-information", "complete", "message", "bell"),
}
_SYSTEM_SOUND_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9 _-]+$")


def resolve_notification_sound(
    app_config: AppConfig,
    *,
    platform: str | None = None,
) -> ResolvedNotificationSound | None:
    """Resolve the configured notification sound exactly once at startup."""
    sound_notifications = app_config.sound_notifications
    enabled = (
        sound_notifications.enabled
        if sound_notifications is not None and sound_notifications.enabled is not None
        else DEFAULT_SOUND_NOTIFICATIONS_ENABLED
    )
    if not enabled:
        return None

    raw_sound = sound_notifications.sound if sound_notifications is not None else None
    volume = (
        sound_notifications.volume
        if sound_notifications is not None and sound_notifications.volume is not None
        else DEFAULT_NOTIFICATION_VOLUME
    )
    resolved_platform = platform or os.sys.platform
    if raw_sound is None or not raw_sound.strip():
        return _resolve_default_notification_sound(resolved_platform, volume)

    sound_setting = raw_sound.strip()
    if not _looks_like_path(sound_setting):
        token = _validate_system_sound_token(sound_setting)
        system_sound_path = resolve_system_sound_path(
            token,
            platform=resolved_platform,
        )
        if system_sound_path is not None:
            return ResolvedNotificationSound(path=system_sound_path, volume=volume)

    resolved_path = _resolve_sound_path_value(sound_setting)
    if not Path(resolved_path).is_file():
        raise ValueError(
            f"'sound_notifications.sound' does not point to an existing file: {resolved_path}"
        )
    return ResolvedNotificationSound(path=resolved_path, volume=volume)


def _looks_like_path(raw: str) -> bool:
    """Return True when a sound setting should be treated as a file path."""
    return (
        "/" in raw
        or "\\" in raw
        or raw.startswith(".")
        or has_home_path_prefix(raw)
        or has_app_path_prefix(raw)
        or Path(raw).suffix != ""
        or Path(raw).is_absolute()
        or is_windows_absolute_path(raw)
    )


def _validate_system_sound_token(raw: str) -> str:
    """Validate a system sound token before embedding it into platform paths."""
    if not _SYSTEM_SOUND_TOKEN_PATTERN.fullmatch(raw):
        raise ValueError(
            "'sound_notifications.sound' is not a valid system sound token"
        )
    return raw


def _resolve_default_notification_sound(
    platform: str,
    volume: float,
) -> ResolvedNotificationSound:
    """Resolve the built-in default sound for one platform."""
    platform_key = "linux" if platform.startswith("linux") else platform
    for token in _DEFAULT_NOTIFICATION_SOUND_TOKENS.get(platform_key, ()):
        path = resolve_system_sound_path(token, platform=platform)
        if path is not None:
            return ResolvedNotificationSound(path=path, volume=volume)
    raise ValueError(
        "Sound notifications are enabled but no default notification sound is available; "
        "set 'sound_notifications.sound' explicitly"
    )


def _resolve_sound_path_value(raw: str) -> str:
    """Resolve a configured sound path using normal PolyChat path rules."""
    if "\x00" in raw:
        raise ValueError("'sound_notifications.sound' contains a NUL character")
    try:
        return map_path(raw)
    except ValueError as e:
        raise ValueError(f"Invalid 'sound_notifications.sound' path: {e}") from e
