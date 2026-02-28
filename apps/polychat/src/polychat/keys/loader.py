"""Unified API key loading interface for PolyChat."""

from typing import Required, TypedDict, cast


class KeyConfig(TypedDict, total=False):
    """Typed configuration for API key loading.

    Discriminated by ``type`` field. Additional fields depend on the type:
      env                      → key
      keychain / credential    → service, account  (aliases; both use keyring)
      json                     → path, key
      direct                   → value (testing only)
    """

    type: Required[str]
    key: str
    value: str
    service: str
    account: str
    path: str


def load_api_key(provider: str, config: KeyConfig) -> str:
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
        {"type": "keychain", "service": "polychat", "account": "claude-key"}  # or "credential"
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

    elif key_type in ("keychain", "credential"):
        from .backends import load_from_keyring

        return load_from_keyring(
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
