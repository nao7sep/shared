"""Tests for keychain key loading."""

import pytest
from unittest.mock import patch
from polychat.keys.backends import load_from_keychain, store_in_keychain


def test_load_from_keychain_success():
    """Test loading API key from keychain."""
    with patch('polychat.keys.backends.keyring') as mock_keyring:
        mock_keyring.get_password.return_value = "sk-test-keychain-key"

        key = load_from_keychain("polychat", "test-account")

        assert key == "sk-test-keychain-key"
        mock_keyring.get_password.assert_called_once_with("polychat", "test-account")


def test_load_from_keychain_missing_key():
    """Test loading when key not found in keychain."""
    with patch('polychat.keys.backends.keyring') as mock_keyring:
        mock_keyring.get_password.return_value = None

        with pytest.raises(ValueError, match="API key not found in keychain"):
            load_from_keychain("polychat", "missing-account")


def test_load_from_keychain_not_installed():
    """Test loading when keyring package not installed."""
    with patch('polychat.keys.backends.keyring', None):
        with pytest.raises(ImportError, match="keyring package not installed"):
            load_from_keychain("polychat", "test-account")


def test_load_from_keychain_access_failure():
    """Test loading when keychain access fails."""
    with patch('polychat.keys.backends.keyring') as mock_keyring:
        mock_keyring.get_password.side_effect = Exception("Access denied")

        with pytest.raises(ValueError, match="Failed to access keychain"):
            load_from_keychain("polychat", "test-account")


def test_store_in_keychain_success():
    """Test storing API key in keychain."""
    with patch('polychat.keys.backends.keyring') as mock_keyring:
        store_in_keychain("polychat", "test-account", "sk-new-key")

        mock_keyring.set_password.assert_called_once_with(
            "polychat", "test-account", "sk-new-key"
        )


def test_store_in_keychain_not_installed():
    """Test storing when keyring package not installed."""
    with patch('polychat.keys.backends.keyring', None):
        with pytest.raises(ImportError, match="keyring package not installed"):
            store_in_keychain("polychat", "test-account", "sk-key")


def test_store_in_keychain_failure():
    """Test storing when operation fails."""
    with patch('polychat.keys.backends.keyring') as mock_keyring:
        mock_keyring.set_password.side_effect = Exception("Write failed")

        with pytest.raises(ValueError, match="Failed to store key in keychain"):
            store_in_keychain("polychat", "test-account", "sk-key")
