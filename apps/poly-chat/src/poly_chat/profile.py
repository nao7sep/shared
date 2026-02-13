"""Profile management for PolyChat.

This module handles loading, validating, and creating user profiles.
Path mapping is handled by the path_mapping module.
"""

import json
from pathlib import Path
from typing import Any

from .path_mapping import map_path
from .prompts import DEFAULT_ASSISTANT_SYSTEM_PROMPT
from .timeouts import DEFAULT_PROFILE_TIMEOUT_SEC


_AI_LIMIT_KEYS = {
    "max_output_tokens",
    "search_max_output_tokens",
}


def _validate_limit_block(block: dict[str, Any], *, context: str) -> None:
    """Validate one ai_limits block."""
    for key, value in block.items():
        if key not in _AI_LIMIT_KEYS:
            raise ValueError(
                f"Unknown ai_limits key '{key}' in {context}. "
                f"Allowed: {', '.join(sorted(_AI_LIMIT_KEYS))}"
            )
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(
                f"ai_limits.{key} in {context} must be a positive integer or null"
            )


def map_system_prompt_path(system_prompt_path: str | None) -> str | None:
    """Map system prompt path to absolute path for file reading.

    Args:
        system_prompt_path: Original system prompt path (with ~, @, or absolute)

    Returns:
        Absolute path string, or None if input is None

    Raises:
        ValueError: If path is relative without special prefix
    """
    if system_prompt_path is None:
        return None

    return map_path(system_prompt_path)


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
        profile["timeout"] = DEFAULT_PROFILE_TIMEOUT_SEC

    # Map all path fields
    profile["chats_dir"] = map_path(profile["chats_dir"])
    profile["logs_dir"] = map_path(profile["logs_dir"])

    # Map all prompt paths
    for prompt_key in ["system_prompt", "title_prompt", "summary_prompt", "safety_prompt"]:
        if prompt_key in profile and isinstance(profile[prompt_key], str):
            profile[prompt_key] = map_path(profile[prompt_key])

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
    required = ["default_ai", "models", "chats_dir", "logs_dir", "api_keys"]

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

    # Validate default_helper_ai if present
    if "default_helper_ai" in profile:
        if profile["default_helper_ai"] not in profile["models"]:
            raise ValueError(f"default_helper_ai '{profile['default_helper_ai']}' not found in models")

    # Validate timeout if present
    if "timeout" in profile:
        timeout = profile["timeout"]
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
            raise ValueError("'timeout' must be a number")
        if timeout < 0:
            raise ValueError("'timeout' cannot be negative")

    # Validate input_mode if present
    if "input_mode" in profile:
        input_mode = profile["input_mode"]
        if not isinstance(input_mode, str):
            raise ValueError("'input_mode' must be a string")
        if input_mode not in ("quick", "compose"):
            raise ValueError("'input_mode' must be 'quick' or 'compose'")

    # Validate api_keys structure
    if not isinstance(profile.get("api_keys"), dict):
        raise ValueError("'api_keys' must be a dictionary")

    # Validate optional ai_limits structure
    ai_limits = profile.get("ai_limits")
    if ai_limits is not None:
        if not isinstance(ai_limits, dict):
            raise ValueError("'ai_limits' must be a dictionary when provided")

        default_limits = ai_limits.get("default")
        if default_limits is not None:
            if not isinstance(default_limits, dict):
                raise ValueError("'ai_limits.default' must be a dictionary")
            _validate_limit_block(default_limits, context="ai_limits.default")

        helper_limits = ai_limits.get("helper")
        if helper_limits is not None:
            if not isinstance(helper_limits, dict):
                raise ValueError("'ai_limits.helper' must be a dictionary")
            _validate_limit_block(helper_limits, context="ai_limits.helper")

        provider_limits = ai_limits.get("providers")
        if provider_limits is not None:
            if not isinstance(provider_limits, dict):
                raise ValueError("'ai_limits.providers' must be a dictionary")
            for provider_name, block in provider_limits.items():
                if not isinstance(block, dict):
                    raise ValueError(
                        f"'ai_limits.providers.{provider_name}' must be a dictionary"
                    )
                _validate_limit_block(
                    block,
                    context=f"ai_limits.providers.{provider_name}",
                )

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


def create_profile(path: str) -> tuple[dict[str, Any], list[str]]:
    """Create new profile template.

    Args:
        path: Where to save the profile

    Returns:
        Tuple of (created profile dictionary, list of status messages for display)
    """
    profile_path = Path(path).expanduser().resolve()

    # Create directory if needed
    profile_path.parent.mkdir(parents=True, exist_ok=True)

    # Collect messages for caller to display
    messages = [
        f"Creating template profile: {profile_path}",
    ]

    # Create profile structure
    # Key order: default_ai, models, timeout, input_mode, prompts, directories, api_keys, ai_limits
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
        "timeout": DEFAULT_PROFILE_TIMEOUT_SEC,
        "input_mode": "quick",
        "system_prompt": "@/prompts/system/default.txt",
        "title_prompt": "@/prompts/title.txt",
        "summary_prompt": "@/prompts/summary.txt",
        "safety_prompt": "@/prompts/safety.txt",
        "chats_dir": "~/poly-chat/chats",
        "logs_dir": "~/poly-chat/logs",
        "api_keys": {
            "openai": {
                "type": "env",
                "key": "OPENAI_API_KEY"
            },
            "claude": {
                "type": "keychain",
                "service": "poly-chat",
                "account": "claude-api-key"
            },
            "gemini": {
                "type": "json",
                "path": "~/.secrets/api-keys.json",
                "key": "gemini"
            },
            "grok": {
                "type": "direct",
                "value": "xai-YOUR-GROK-API-KEY-HERE"
            },
            "perplexity": {
                "type": "env",
                "key": "PERPLEXITY_API_KEY"
            },
            "mistral": {
                "type": "env",
                "key": "MISTRAL_API_KEY"
            },
            "deepseek": {
                "type": "env",
                "key": "DEEPSEEK_API_KEY"
            }
        },
        "ai_limits": {
            "default": {
                "max_output_tokens": None,
                "search_max_output_tokens": None,
            },
            "providers": {
                "claude": {
                    "max_output_tokens": None,
                    "search_max_output_tokens": None,
                }
            },
            "helper": {
                "max_output_tokens": None,
                "search_max_output_tokens": None,
            },
        },
    }

    # Save profile
    with open(profile_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)

    # Add success and next steps messages
    messages.extend([
        "",  # Empty line
        "Template profile created successfully!",
        "",  # Empty line
        "Next steps:",
        f"  1. Edit {profile_path}",
        "     Update model names, paths, and API key placeholders",
        "",  # Empty line
        "  2. Start PolyChat:",
        f"     poetry run pc -p {profile_path}",
    ])

    return profile, messages
