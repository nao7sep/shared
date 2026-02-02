"""JSON file API key loading for PolyChat."""

import json
from pathlib import Path


def load_from_json(file_path: str, key_name: str) -> str:
    """Load API key from JSON file.

    Args:
        file_path: Path to JSON file (already mapped)
        key_name: Key name in JSON (supports nested like "openai.api_key")

    Returns:
        API key string

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If key not found or file invalid

    Example JSON file:
    {
      "openai": "sk-...",
      "claude": "sk-ant-...",
      "nested": {
        "gemini": "..."
      }
    }
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"API key file not found: {file_path}\n"
            f"Create it with appropriate API keys"
        )

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {file_path}: {e}")

    # Support nested keys with dot notation
    value = data
    for part in key_name.split("."):
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            raise ValueError(
                f"Key '{key_name}' not found in {file_path}\n"
                f"Available keys: {', '.join(data.keys())}"
            )

    if not isinstance(value, str):
        raise ValueError(
            f"Key '{key_name}' in {file_path} is not a string"
        )

    return value.strip()
