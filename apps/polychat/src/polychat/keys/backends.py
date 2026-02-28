"""Credential backend loaders for environment, JSON, and system credential store."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

_keyring: Any | None
try:
    import keyring as _keyring
except ImportError:
    _keyring = None

keyring = _keyring


def _credential_store_name() -> str:
    """Return a human-readable name for the platform's credential store."""
    if sys.platform == "darwin":
        return "macOS Keychain"
    elif sys.platform == "win32":
        return "Windows Credential Manager"
    else:
        return "system credential store"


def _credential_store_hint(service: str, account: str) -> str:
    """Return a platform-appropriate command to add a credential."""
    if sys.platform == "darwin":
        return (
            f"Add it with: security add-generic-password "
            f"-s {service} -a {account} -w your-api-key"
        )
    elif sys.platform == "win32":
        return (
            f"Add it with: cmdkey /generic:{service} "
            f"/user:{account} /pass:your-api-key"
        )
    else:
        return (
            f"Add it with: secret-tool store --label='{service}' "
            f"service {service} account {account}"
        )


def load_from_env(var_name: str) -> str:
    """Load API key from environment variable."""
    value = os.environ.get(var_name)

    if not value:
        raise ValueError(
            f"Environment variable '{var_name}' not set.\n"
            f"Set it with:\n"
            f"  Unix/macOS:  export {var_name}=your-api-key\n"
            f"  Windows CMD: set {var_name}=your-api-key\n"
            f"  PowerShell:  $env:{var_name} = 'your-api-key'"
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


def load_from_keyring(service: str, account: str) -> str:
    """Load API key from the system credential store via keyring."""
    if keyring is None:
        raise ImportError(
            "keyring package not installed.\n" "Install with: uv add keyring"
        )

    store_name = _credential_store_name()
    try:
        key = keyring.get_password(service, account)
    except Exception as e:
        raise ValueError(
            f"Failed to access {store_name}: {e}\n"
            f"Service: {service}, Account: {account}"
        )

    if not isinstance(key, str) or not key:
        raise ValueError(
            f"API key not found in {store_name}.\n"
            f"Service: {service}, Account: {account}\n"
            f"{_credential_store_hint(service, account)}"
        )

    return key


def store_in_keyring(service: str, account: str, key: str) -> None:
    """Store API key in the system credential store via keyring."""
    if keyring is None:
        raise ImportError("keyring package not installed")

    store_name = _credential_store_name()
    try:
        keyring.set_password(service, account, key)
    except Exception as e:
        raise ValueError(f"Failed to store key in {store_name}: {e}")


# Backward-compatible aliases
load_from_keychain = load_from_keyring
store_in_keychain = store_in_keyring
load_from_credential_manager = load_from_keyring
store_in_credential_manager = store_in_keyring
