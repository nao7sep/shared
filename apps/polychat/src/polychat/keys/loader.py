"""Unified API key loading interface for PolyChat."""

from typing import Any, cast


def load_api_key(provider: str, config: dict[str, Any]) -> str:
    """Load API key based on configuration.

    Args:
        provider: AI provider name (openai, claude, etc.)
        config: Key configuration from profile

    Returns:
        API key string

    Raises:
        ValueError: If key cannot be loaded

    Example configs:
        {"type": "env", "key": "OPENAI_API_KEY"}
        {"type": "keychain", "service": "polychat", "account": "claude-key"}
        {"type": "credential", "service": "polychat", "account": "claude-key"}
        {"type": "json", "path": "~/.secrets/keys.json", "key": "gemini"}
        {"type": "direct", "value": "sk-..."} (testing only)
    """
    key_type = config.get("type")

    if key_type == "direct":
        # Direct value (for testing)
        return cast(str, config["value"])

    elif key_type == "env":
        from .backends import load_from_env

        return load_from_env(cast(str, config["key"]))

    elif key_type == "keychain":
        from .backends import load_from_keychain

        return load_from_keychain(
            cast(str, config["service"]),
            cast(str, config["account"]),
        )

    elif key_type == "credential":
        from .backends import load_from_credential_manager

        return load_from_credential_manager(
            cast(str, config["service"]),
            cast(str, config["account"]),
        )

    elif key_type == "json":
        from .backends import load_from_json

        return load_from_json(cast(str, config["path"]), cast(str, config["key"]))

    else:
        raise ValueError(f"Unknown key type '{key_type}' for provider '{provider}'")


def validate_api_key(key: str, provider: str) -> bool:
    """Basic validation of API key.

    Args:
        key: API key to validate
        provider: Provider name (for provider-specific validation)

    Returns:
        True if key looks valid

    Note: This is basic validation (non-empty, reasonable length).
    Actual validation happens when making API calls.
    """
    if not key or not key.strip():
        return False

    # Most API keys are at least 20 characters
    if len(key.strip()) < 20:
        return False

    return True
