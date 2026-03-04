"""Typed app-config models used at config file boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


_KNOWN_SOUND_NOTIFICATION_KEYS = {
    "enabled",
    "sound",
    "volume",
}

_KNOWN_TEXT_COLOR_KEYS = {
    "user_input",
    "cost_line",
}

_KNOWN_APP_CONFIG_KEYS = {
    "sound_notifications",
    "text_colors",
}


@dataclass(slots=True)
class SoundNotificationsConfig:
    """Typed sound-notification settings from one config file."""

    enabled: bool | None
    sound: str | None
    volume: float | None
    extras: dict[str, Any]

    @classmethod
    def from_dict(
        cls,
        raw: Mapping[str, Any],
    ) -> SoundNotificationsConfig:
        """Create typed sound settings from raw config data."""
        if not isinstance(raw, Mapping):
            raise ValueError("'sound_notifications' must be a dictionary")

        enabled = raw.get("enabled")
        if enabled is not None and not isinstance(enabled, bool):
            raise ValueError("'sound_notifications.enabled' must be a boolean or null")

        sound = raw.get("sound")
        if sound is not None and not isinstance(sound, str):
            raise ValueError("'sound_notifications.sound' must be a string or null")

        volume = raw.get("volume")
        if volume is not None:
            if isinstance(volume, bool) or not isinstance(volume, (int, float)):
                raise ValueError("'sound_notifications.volume' must be a number or null")
            if not 0 <= float(volume) <= 1:
                raise ValueError(
                    "'sound_notifications.volume' must be between 0 and 1"
                )

        extras = {
            str(key): value
            for key, value in raw.items()
            if key not in _KNOWN_SOUND_NOTIFICATION_KEYS
        }
        return cls(
            enabled=enabled,
            sound=sound,
            volume=float(volume) if volume is not None else None,
            extras=extras,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize sound-notification settings for JSON persistence."""
        payload: dict[str, Any] = {
            "enabled": self.enabled,
            "sound": self.sound,
            "volume": self.volume,
        }
        payload.update(self.extras)
        return payload


@dataclass(slots=True)
class TextColorsConfig:
    """Typed text-color settings from one config file."""

    user_input: str | None
    cost_line: str | None
    extras: dict[str, Any]

    @classmethod
    def from_dict(
        cls,
        raw: Mapping[str, Any],
    ) -> TextColorsConfig:
        """Create typed text-color settings from raw config data."""
        if not isinstance(raw, Mapping):
            raise ValueError("'text_colors' must be a dictionary")

        user_input = raw.get("user_input")
        if user_input is not None and not isinstance(user_input, str):
            raise ValueError("'text_colors.user_input' must be a string or null")

        cost_line = raw.get("cost_line")
        if cost_line is not None and not isinstance(cost_line, str):
            raise ValueError("'text_colors.cost_line' must be a string or null")

        extras = {
            str(key): value
            for key, value in raw.items()
            if key not in _KNOWN_TEXT_COLOR_KEYS
        }
        return cls(
            user_input=user_input,
            cost_line=cost_line,
            extras=extras,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize text-color settings for JSON persistence."""
        payload: dict[str, Any] = {
            "user_input": self.user_input,
            "cost_line": self.cost_line,
        }
        payload.update(self.extras)
        return payload


@dataclass(slots=True)
class AppConfig:
    """Typed app-config view consumed by startup and UI layers."""

    sound_notifications: SoundNotificationsConfig | None
    text_colors: TextColorsConfig | None
    extras: dict[str, Any]

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> AppConfig:
        """Create typed app config from raw config data."""
        if not isinstance(raw, Mapping):
            raise ValueError("App config must be a mapping")

        sound_notifications_raw = raw.get("sound_notifications")
        if sound_notifications_raw is None:
            sound_notifications = None
        else:
            sound_notifications = SoundNotificationsConfig.from_dict(
                sound_notifications_raw
            )

        text_colors_raw = raw.get("text_colors")
        if text_colors_raw is None:
            text_colors = None
        else:
            text_colors = TextColorsConfig.from_dict(text_colors_raw)

        extras = {
            str(key): value
            for key, value in raw.items()
            if key not in _KNOWN_APP_CONFIG_KEYS
        }

        return cls(
            sound_notifications=sound_notifications,
            text_colors=text_colors,
            extras=extras,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize app config for JSON persistence."""
        payload: dict[str, Any] = {}
        if self.sound_notifications is not None:
            payload["sound_notifications"] = self.sound_notifications.to_dict()
        if self.text_colors is not None:
            payload["text_colors"] = self.text_colors.to_dict()
        payload.update(self.extras)
        return payload
