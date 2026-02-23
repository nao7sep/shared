"""Helper functions for integration tests with real API keys."""

import json
from pathlib import Path
from typing import Optional

_DEV_API_KEYS_FILENAME = ".dev-api-keys.json"
_config_cache: Optional[dict] = None


def find_test_api_keys_file() -> Optional[Path]:
    """
    Search for .dev-api-keys.json by recursively checking parent directories.

    Starts from the current file's directory and moves up until:
    - File is found (returns Path)
    - Filesystem root is reached (returns None)

    This allows placing the file outside the repo if needed.
    """
    current = Path(__file__).resolve().parent

    while True:
        candidate = current / _DEV_API_KEYS_FILENAME
        if candidate.exists():
            return candidate

        # Check if we've reached filesystem root
        parent = current.parent
        if parent == current:
            # Can't go higher
            return None

        current = parent


def load_test_config() -> dict:
    """
    Load test API keys configuration.

    Returns the full config dict. Caches result after first load.
    Raises FileNotFoundError if .dev-api-keys.json is not found.
    """
    global _config_cache

    if _config_cache is not None:
        return _config_cache

    config_file = find_test_api_keys_file()
    if config_file is None:
        raise FileNotFoundError(
            f"{_DEV_API_KEYS_FILENAME} not found in current directory or any parent directory. "
            "Create this file in your home directory (~) or any parent directory with API keys for testing."
        )

    with open(config_file, 'r', encoding='utf-8') as f:
        _config_cache = json.load(f)

    return _config_cache


def is_ai_available(ai_name: str) -> bool:
    """
    Check if an AI provider is available for testing.

    Returns True if:
    - The AI exists in config
    - It has a non-empty api_key

    Args:
        ai_name: Provider name (e.g., "openai", "claude", "gemini")

    Returns:
        True if AI can be tested, False otherwise
    """
    try:
        config = load_test_config()
    except FileNotFoundError:
        return False

    if ai_name not in config:
        return False

    ai_config = config[ai_name]
    api_key = ai_config.get("api_key", "")

    return bool(api_key and api_key.strip())


def get_ai_config(ai_name: str) -> dict:
    """
    Get configuration for a specific AI provider.

    Args:
        ai_name: Provider name (e.g., "openai", "claude")

    Returns:
        Dict with api_key, model, and other parameters

    Raises:
        KeyError: If AI not found in config
        FileNotFoundError: If config file not found
    """
    config = load_test_config()
    return config[ai_name]
