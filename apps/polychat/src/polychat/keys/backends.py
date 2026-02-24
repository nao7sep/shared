"""Credential backend loaders for environment, JSON, keychain, and credential manager."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

_keyring: Any | None
try:
    import keyring as _keyring
except ImportError:
    _keyring = None

keyring = _keyring


def load_from_env(var_name: str) -> str:
    """Load API key from environment variable."""
    value = os.environ.get(var_name)

    if not value:
        raise ValueError(
            f"Environment variable '{var_name}' not set.\n"
            f"Set it with: export {var_name}=your-api-key"
        )

    return value.strip()


def load_from_json(file_path: str, key_name: str) -> str:
    """Load API key from JSON file."""
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
    value: Any = data
    for part in key_name.split("."):
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            raise ValueError(
                f"Key '{key_name}' not found in {file_path}\n"
                f"Available keys: {', '.join(data.keys())}"
            )

    if not isinstance(value, str):
        raise ValueError(f"Key '{key_name}' in {file_path} is not a string")

    return value.strip()


def load_from_keychain(service: str, account: str) -> str:
    """Load API key from macOS Keychain."""
    if keyring is None:
        raise ImportError(
            "keyring package not installed.\n" "Install with: uv add keyring"
        )

    try:
        key = keyring.get_password(service, account)
    except Exception as e:
        raise ValueError(
            f"Failed to access keychain: {e}\n"
            f"Service: {service}, Account: {account}"
        )

    if not isinstance(key, str) or not key:
        raise ValueError(
            f"API key not found in keychain.\n"
            f"Service: {service}, Account: {account}\n"
            f"Add it with: security add-generic-password "
            f"-s {service} -a {account} -w your-api-key"
        )

    return key


def store_in_keychain(service: str, account: str, key: str) -> None:
    """Store API key in macOS Keychain."""
    if keyring is None:
        raise ImportError("keyring package not installed")

    try:
        keyring.set_password(service, account, key)
    except Exception as e:
        raise ValueError(f"Failed to store key in keychain: {e}")


def load_from_credential_manager(service: str, account: str) -> str:
    """Load API key from Windows Credential Manager."""
    if keyring is None:
        raise ImportError(
            "keyring package not installed.\n" "Install with: uv add keyring"
        )

    try:
        key = keyring.get_password(service, account)
    except Exception as e:
        raise ValueError(
            f"Failed to access Windows Credential Manager: {e}\n"
            f"Service: {service}, Account: {account}"
        )

    if not isinstance(key, str) or not key:
        raise ValueError(
            f"API key not found in Windows Credential Manager.\n"
            f"Service: {service}, Account: {account}\n"
            f"Add it with: cmdkey /generic:{service} /user:{account} /pass:your-api-key"
        )

    return key


def store_in_credential_manager(service: str, account: str, key: str) -> None:
    """Store API key in Windows Credential Manager."""
    if keyring is None:
        raise ImportError("keyring package not installed")

    try:
        keyring.set_password(service, account, key)
    except Exception as e:
        raise ValueError(f"Failed to store key in Windows Credential Manager: {e}")
