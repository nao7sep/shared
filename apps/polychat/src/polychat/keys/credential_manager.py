"""Windows Credential Manager API key loading for PolyChat."""

from typing import Any

_keyring: Any | None
try:
    import keyring as _keyring
except ImportError:
    _keyring = None

keyring = _keyring


def load_from_credential_manager(service: str, account: str) -> str:
    """Load API key from Windows Credential Manager.

    Args:
        service: Credential target name (e.g., "polychat")
        account: Credential user name (e.g., "claude-api-key")

    Returns:
        API key string

    Raises:
        ImportError: If keyring package not installed
        ValueError: If key not found in Credential Manager

    Note: Uses the same keyring library as macOS Keychain, backed by
    Windows Credential Locker (WinVaultKeyring) on Windows.
    """
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
    """Store API key in Windows Credential Manager.

    Args:
        service: Credential target name
        account: Credential user name
        key: API key to store

    Raises:
        ImportError: If keyring package not installed
        ValueError: If storing fails
    """
    if keyring is None:
        raise ImportError("keyring package not installed")

    try:
        keyring.set_password(service, account, key)
    except Exception as e:
        raise ValueError(f"Failed to store key in Windows Credential Manager: {e}")
