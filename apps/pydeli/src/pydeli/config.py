from __future__ import annotations

import json
from pathlib import Path

from .errors import ConfigError
from .models import RegistryTarget
from .output_segments import start_segment

CONFIG_DIR = Path.home() / ".pydeli"
CONFIG_FILENAME = "config.json"
CONFIG_PATH = CONFIG_DIR / CONFIG_FILENAME

_EMPTY_CONFIG: dict[str, dict] = {"tokens": {}}


def load_config() -> dict:
    """Load config from disk, creating it if it does not exist."""
    if not CONFIG_PATH.exists():
        _create_default_config()

    try:
        text = CONFIG_PATH.read_text(encoding="utf-8")
        data = json.loads(text)
    except (json.JSONDecodeError, OSError) as exc:
        raise ConfigError(f"Failed to read config file: {CONFIG_PATH}: {exc}") from exc

    if not isinstance(data, dict):
        raise ConfigError(f"Config file must contain a JSON object: {CONFIG_PATH}")
    if "tokens" not in data:
        data["tokens"] = {}
    return data


def save_config(data: dict) -> None:
    """Write config to disk."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        CONFIG_PATH.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise ConfigError(f"Failed to write config file: {CONFIG_PATH}: {exc}") from exc


def get_token(config: dict, app_name: str, target: RegistryTarget) -> str | None:
    """Return the stored token for an app + registry, or None if not set."""
    tokens = config.get("tokens", {})
    app_tokens = tokens.get(app_name, {})
    value = app_tokens.get(target.value)
    if isinstance(value, str) and value:
        return value
    return None


def set_token(config: dict, app_name: str, target: RegistryTarget, token: str) -> None:
    """Store a token for an app + registry in the config dict (caller must save)."""
    tokens = config.setdefault("tokens", {})
    app_tokens = tokens.setdefault(app_name, {})
    app_tokens[target.value] = token


def _create_default_config() -> None:
    """Create the config directory and file with empty defaults."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps(_EMPTY_CONFIG, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    start_segment()
    print(f"Created config file: {CONFIG_PATH}")
    print("This file stores your PyPI/TestPyPI tokens for each app.")
