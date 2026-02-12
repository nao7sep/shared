"""macOS Keychain API key loading for PolyChat."""

try:
    import keyring
except ImportError:
    keyring = None


def load_from_keychain(service: str, account: str) -> str:
    """Load API key from macOS Keychain.

    Args:
        service: Keychain service name (e.g., "poly-chat")
        account: Keychain account name (e.g., "claude-api-key")

    Returns:
        API key string

    Raises:
        ImportError: If keyring package not installed
        ValueError: If key not found in keychain

    Note: First access will require user approval via macOS system dialog.
    """
    if keyring is None:
        raise ImportError(
            "keyring package not installed.\n" "Install with: poetry add keyring"
        )

    try:
        key = keyring.get_password(service, account)
    except Exception as e:
        raise ValueError(
            f"Failed to access keychain: {e}\n"
            f"Service: {service}, Account: {account}"
        )

    if not key:
        raise ValueError(
            f"API key not found in keychain.\n"
            f"Service: {service}, Account: {account}\n"
            f"Add it with: security add-generic-password "
            f"-s {service} -a {account} -w your-api-key"
        )

    return key


def store_in_keychain(service: str, account: str, key: str) -> None:
    """Store API key in macOS Keychain.

    Args:
        service: Keychain service name
        account: Keychain account name
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
        raise ValueError(f"Failed to store key in keychain: {e}")
