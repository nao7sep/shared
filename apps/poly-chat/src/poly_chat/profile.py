"""Profile management for PolyChat.

This module handles loading, validating, and creating user profiles,
as well as path mapping for special prefixes (~, @).
"""

import json
from pathlib import Path
from typing import Any


def map_path(path: str) -> str:
    """Map path with special prefixes to absolute path.

    Args:
        path: Path to map (can have ~, @, or be absolute)

    Returns:
        Absolute path string

    Raises:
        ValueError: If path is relative without special prefix
    """
    # Handle tilde (home directory)
    if path.startswith("~/"):
        return str(Path.home() / path[2:])
    elif path == "~":
        return str(Path.home())

    # Handle @ (app root directory)
    elif path.startswith("@/"):
        # App root is where pyproject.toml is (poly-chat/)
        app_root = Path(__file__).parent.parent.parent
        return str(app_root / path[2:])
    elif path == "@":
        app_root = Path(__file__).parent.parent.parent
        return str(app_root)

    # Absolute path - use as-is
    elif Path(path).is_absolute():
        return str(Path(path))

    # Relative path without prefix - ERROR
    else:
        raise ValueError(
            f"Relative paths without prefix are not supported: {path}\n"
            f"Use '~/' for home directory, '@/' for app directory, "
            f"or provide absolute path"
        )


def load_profile(path: str) -> dict[str, Any]:
    """Load profile from JSON file.

    Args:
        path: Path to profile file (can have ~, absolute)

    Returns:
        Profile dictionary with absolute paths

    Raises:
        FileNotFoundError: If profile doesn't exist
        ValueError: If profile structure is invalid
        json.JSONDecodeError: If JSON is malformed
    """
    # Expand ~ if present
    profile_path = Path(path).expanduser().resolve()

    if not profile_path.exists():
        raise FileNotFoundError(
            f"Profile not found: {profile_path}\n"
            f"Create a new profile with: pc init {path}"
        )

    # Load JSON
    with open(profile_path, "r", encoding="utf-8") as f:
        profile = json.load(f)

    # Validate required fields
    validate_profile(profile)

    # Set default timeout if not present
    if "timeout" not in profile:
        profile["timeout"] = 30

    # Map all path fields
    profile["chats_dir"] = map_path(profile["chats_dir"])
    profile["log_dir"] = map_path(profile["log_dir"])

    # Map system_prompt if it's a path (string)
    if isinstance(profile.get("system_prompt"), str):
        profile["system_prompt"] = map_path(profile["system_prompt"])
    # If it's a dict with type="text", leave as-is

    # Map API key paths (for type="json")
    for provider, key_config in profile.get("api_keys", {}).items():
        if isinstance(key_config, dict) and key_config.get("type") == "json":
            key_config["path"] = map_path(key_config["path"])

    return profile


def validate_profile(profile: dict[str, Any]) -> None:
    """Validate profile structure.

    Args:
        profile: Profile dictionary

    Raises:
        ValueError: If profile is invalid
    """
    required = ["default_ai", "models", "chats_dir", "log_dir", "api_keys"]

    missing = [f for f in required if f not in profile]
    if missing:
        raise ValueError(f"Profile missing required fields: {', '.join(missing)}")

    # Validate models is a dict and non-empty
    if not isinstance(profile["models"], dict):
        raise ValueError("'models' must be a dictionary")

    if not profile["models"]:
        raise ValueError("'models' cannot be empty")

    # Validate default_ai is in models
    if profile["default_ai"] not in profile["models"]:
        raise ValueError(f"default_ai '{profile['default_ai']}' not found in models")

    # Validate timeout if present
    if "timeout" in profile:
        timeout = profile["timeout"]
        if not isinstance(timeout, (int, float)):
            raise ValueError("'timeout' must be a number")
        if timeout < 0:
            raise ValueError("'timeout' cannot be negative")

    # Validate api_keys structure
    if not isinstance(profile.get("api_keys"), dict):
        raise ValueError("'api_keys' must be a dictionary")

    # Validate each api_key configuration
    for provider, key_config in profile.get("api_keys", {}).items():
        if not isinstance(key_config, dict):
            raise ValueError(f"API key config for '{provider}' must be a dictionary")

        if "type" not in key_config:
            raise ValueError(f"API key config for '{provider}' missing 'type' field")

        key_type = key_config["type"]

        # Validate type-specific required fields
        if key_type == "env":
            if "key" not in key_config:
                raise ValueError(f"API key config for '{provider}' (type=env) missing 'key' field")
        elif key_type == "keychain":
            if "service" not in key_config:
                raise ValueError(f"API key config for '{provider}' (type=keychain) missing 'service' field")
            if "account" not in key_config:
                raise ValueError(f"API key config for '{provider}' (type=keychain) missing 'account' field")
        elif key_type == "json":
            if "path" not in key_config:
                raise ValueError(f"API key config for '{provider}' (type=json) missing 'path' field")
            if "key" not in key_config:
                raise ValueError(f"API key config for '{provider}' (type=json) missing 'key' field")
        elif key_type == "direct":
            if "value" not in key_config:
                raise ValueError(f"API key config for '{provider}' (type=direct) missing 'value' field")
        else:
            raise ValueError(f"API key config for '{provider}' has unknown type '{key_type}'")


def create_profile(path: str) -> dict[str, Any]:
    """Create new profile template with accompanying API keys file.

    Args:
        path: Where to save the profile

    Returns:
        Created profile dictionary
    """
    profile_path = Path(path).expanduser().resolve()

    # Create directory if needed
    profile_path.parent.mkdir(parents=True, exist_ok=True)

    # Create API keys file next to profile
    api_keys_path = profile_path.parent / "api-keys.json"

    print(f"Creating template profile: {profile_path}")
    print(f"Creating template API keys: {api_keys_path}")

    # Create template API keys file
    api_keys_template = {
        "openai": "sk-YOUR-OPENAI-API-KEY-HERE",
        "claude": "sk-ant-YOUR-CLAUDE-API-KEY-HERE",
        "gemini": "YOUR-GEMINI-API-KEY-HERE",
        "grok": "xai-YOUR-GROK-API-KEY-HERE",
        "perplexity": "pplx-YOUR-PERPLEXITY-API-KEY-HERE",
        "mistral": "YOUR-MISTRAL-API-KEY-HERE",
        "deepseek": "sk-YOUR-DEEPSEEK-API-KEY-HERE"
    }

    with open(api_keys_path, "w", encoding="utf-8") as f:
        json.dump(api_keys_template, f, indent=2, ensure_ascii=False)

    # Determine relative path from profile to API keys file
    # Use @ prefix if both are in same directory, otherwise use absolute path
    if api_keys_path.parent == profile_path.parent:
        api_keys_ref = f"@/{api_keys_path.name}"
    else:
        api_keys_ref = str(api_keys_path)

    # Create profile structure
    profile = {
        "default_ai": "claude",
        "models": {
            "openai": "gpt-5-mini",
            "claude": "claude-haiku-4-5",
            "gemini": "gemini-3-flash-preview",
            "grok": "grok-4-1-fast-non-reasoning",
            "perplexity": "sonar",
            "mistral": "mistral-small-latest",
            "deepseek": "deepseek-chat"
        },
        "timeout": 30,
        "system_prompt": "@/system-prompts/default.txt",
        "chats_dir": "@/chats",
        "log_dir": "@/logs",
        "api_keys": {
            "openai": {
                "type": "json",
                "path": api_keys_ref,
                "key": "openai"
            },
            "claude": {
                "type": "json",
                "path": api_keys_ref,
                "key": "claude"
            },
            "gemini": {
                "type": "json",
                "path": api_keys_ref,
                "key": "gemini"
            },
            "grok": {
                "type": "json",
                "path": api_keys_ref,
                "key": "grok"
            },
            "perplexity": {
                "type": "json",
                "path": api_keys_ref,
                "key": "perplexity"
            },
            "mistral": {
                "type": "json",
                "path": api_keys_ref,
                "key": "mistral"
            },
            "deepseek": {
                "type": "json",
                "path": api_keys_ref,
                "key": "deepseek"
            }
        }
    }

    # Save profile
    with open(profile_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)

    print()
    print("Template files created successfully!")
    print()
    print("Next steps:")
    print(f"  1. Edit {api_keys_path}")
    print("     Replace placeholder API keys with your actual keys")
    print()
    print(f"  2. Start PolyChat:")
    print(f"     poetry run pc -p {profile_path}")

    return profile
