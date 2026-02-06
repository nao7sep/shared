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

    # Validate default_ai is in models
    if profile["default_ai"] not in profile["models"]:
        raise ValueError(f"default_ai '{profile['default_ai']}' not found in models")

    # Validate models is a dict
    if not isinstance(profile["models"], dict):
        raise ValueError("'models' must be a dictionary")

    # Validate api_keys structure
    if not isinstance(profile.get("api_keys"), dict):
        raise ValueError("'api_keys' must be a dictionary")


def create_profile(path: str) -> dict[str, Any]:
    """Create new profile with interactive wizard.

    Args:
        path: Where to save the profile

    Returns:
        Created profile dictionary
    """
    profile_path = Path(path).expanduser().resolve()

    # Create directory if needed
    profile_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Creating new profile: {profile_path}")
    print()

    # Interactive prompts
    print("Available AI providers:")
    print("  1. OpenAI (GPT)")
    print("  2. Claude (Anthropic)")
    print("  3. Gemini (Google)")
    print("  4. Grok (xAI)")
    print("  5. Perplexity")
    print("  6. Mistral")
    print("  7. DeepSeek")

    provider_map = {
        "1": "openai",
        "2": "claude",
        "3": "gemini",
        "4": "grok",
        "5": "perplexity",
        "6": "mistral",
        "7": "deepseek",
    }

    choice = input("Select default AI (1-7) [2]: ").strip() or "2"
    default_ai = provider_map.get(choice, "claude")

    # Get chats directory
    default_chats_dir = "~/poly-chat-logs"
    chats_dir = (
        input(f"Chat history directory [{default_chats_dir}]: ").strip()
        or default_chats_dir
    )

    # Get error log directory
    default_log_dir = f"{chats_dir}/logs"
    log_dir = input(f"Error log directory [{default_log_dir}]: ").strip() or default_log_dir

    # Create profile structure
    profile = {
        "default_ai": default_ai,
        "timeout": 30,
        "models": {
            "openai": "gpt-5-mini",
            "claude": "claude-haiku-4-5",
            "gemini": "gemini-3-flash-preview",
            "grok": "grok-4-1-fast-non-reasoning",
            "perplexity": "sonar",
            "mistral": "mistral-small-latest",
            "deepseek": "deepseek-chat",
        },
        "system_prompt": "@/system-prompts/default.txt",
        "chats_dir": chats_dir,
        "log_dir": log_dir,
        "api_keys": {},
    }

    # Configure API keys
    print("\nAPI Key Configuration")
    print("Options: [e]nv variable, [k]eychain, [j]son file, [s]kip")

    for provider in profile["models"].keys():
        print(f"\n{provider.upper()} API key:")
        choice = input("  Configure as (e/k/j/s) [s]: ").strip().lower() or "s"

        if choice == "e":
            var_name = input(
                "  Environment variable name [" + f"{provider.upper()}_API_KEY]: "
            ).strip()
            var_name = var_name or f"{provider.upper()}_API_KEY"
            profile["api_keys"][provider] = {"type": "env", "key": var_name}

        elif choice == "k":
            service = input("  Keychain service [poly-chat]: ").strip() or "poly-chat"
            account = input(f"  Keychain account [{provider}-api-key]: ").strip()
            account = account or f"{provider}-api-key"
            profile["api_keys"][provider] = {
                "type": "keychain",
                "service": service,
                "account": account,
            }

        elif choice == "j":
            json_path = input("  JSON file path [~/.secrets/api-keys.json]: ").strip()
            json_path = json_path or "~/.secrets/api-keys.json"
            key_name = input(f"  Key in JSON [{provider}]: ").strip() or provider
            profile["api_keys"][provider] = {
                "type": "json",
                "path": json_path,
                "key": key_name,
            }

    # Save profile
    with open(profile_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)

    print(f"\nProfile created: {profile_path}")
    return profile
