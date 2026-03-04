"""App-config file operations."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, cast

from ..constants import DEFAULT_APP_CONFIG_PATH
from ..domain.config import AppConfig
from ..path_utils import map_path


def default_config_path() -> str:
    """Return the mapped default app-config path."""
    return map_path(DEFAULT_APP_CONFIG_PATH)


def _write_json_atomically(path: Path, payload: Any) -> None:
    """Write JSON via a temp file and atomically replace the destination."""
    path.parent.mkdir(parents=True, exist_ok=True)

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            json.dump(payload, temp_file, indent=2, ensure_ascii=False)
            temp_file.flush()
            os.fsync(temp_file.fileno())
            temp_path = Path(temp_file.name)

        os.replace(temp_path, path)
    except Exception:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise


def _build_default_config_template() -> dict[str, Any]:
    """Build the persisted first-run config template."""
    return {
        "sound_notifications": {
            "enabled": None,
            "sound": None,
            "volume": None,
        },
        "text_colors": {
            "user_input": None,
            "cost_line": None,
        },
    }


def load_config(path: str) -> AppConfig:
    """Load app config from JSON file."""
    config_path = Path(path).resolve()

    if not config_path.exists():
        raise FileNotFoundError(f"App config not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = cast(dict[str, Any], json.load(f))

    validate_config(config)
    return AppConfig.from_dict(config)


def validate_config(config: dict[str, Any]) -> None:
    """Validate raw app-config structure before conversion to AppConfig."""
    if not isinstance(config, dict):
        raise ValueError("App config must be a JSON object")

    sound_notifications = config.get("sound_notifications")
    if sound_notifications is not None:
        if not isinstance(sound_notifications, dict):
            raise ValueError("'sound_notifications' must be a dictionary")
        enabled = sound_notifications.get("enabled")
        if enabled is not None and not isinstance(enabled, bool):
            raise ValueError("'sound_notifications.enabled' must be a boolean or null")
        sound = sound_notifications.get("sound")
        if sound is not None and not isinstance(sound, str):
            raise ValueError("'sound_notifications.sound' must be a string or null")
        volume = sound_notifications.get("volume")
        if volume is not None:
            if isinstance(volume, bool) or not isinstance(volume, (int, float)):
                raise ValueError("'sound_notifications.volume' must be a number or null")
            if not 0 <= float(volume) <= 1:
                raise ValueError(
                    "'sound_notifications.volume' must be between 0 and 1"
                )

    text_colors = config.get("text_colors")
    if text_colors is not None:
        if not isinstance(text_colors, dict):
            raise ValueError("'text_colors' must be a dictionary")
        user_input = text_colors.get("user_input")
        if user_input is not None and not isinstance(user_input, str):
            raise ValueError("'text_colors.user_input' must be a string or null")
        cost_line = text_colors.get("cost_line")
        if cost_line is not None and not isinstance(cost_line, str):
            raise ValueError("'text_colors.cost_line' must be a string or null")


def create_config(path: str) -> tuple[dict[str, Any], list[str]]:
    """Create a new app-config template."""
    config_path = Path(path).resolve()
    template = _build_default_config_template()

    runtime_config = AppConfig.from_dict(template)
    persistable_config = runtime_config.to_dict()
    _write_json_atomically(config_path, persistable_config)

    return persistable_config, [f"Created app config: {config_path}"]
