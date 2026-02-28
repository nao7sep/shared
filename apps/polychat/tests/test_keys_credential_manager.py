"""Tests for Windows Credential Manager key loading."""

import pytest
from unittest.mock import patch
from polychat.keys.backends import (
    load_from_credential_manager,
    store_in_credential_manager,
)


def test_load_from_credential_manager_success():
    """Test loading API key from Windows Credential Manager."""
    with patch('polychat.keys.backends.keyring') as mock_keyring:
        mock_keyring.get_password.return_value = "sk-test-credential-key"

        key = load_from_credential_manager("polychat", "test-account")

        assert key == "sk-test-credential-key"
        mock_keyring.get_password.assert_called_once_with("polychat", "test-account")


def test_load_from_credential_manager_missing_key():
    """Test loading when key not found in Credential Manager."""
    with patch('polychat.keys.backends.keyring') as mock_keyring:
        mock_keyring.get_password.return_value = None

        with pytest.raises(ValueError, match="API key not found in"):
            load_from_credential_manager("polychat", "missing-account")


def test_load_from_credential_manager_not_installed():
    """Test loading when keyring package not installed."""
    with patch('polychat.keys.backends.keyring', None):
        with pytest.raises(ImportError, match="keyring package not installed"):
            load_from_credential_manager("polychat", "test-account")


def test_load_from_credential_manager_access_failure():
    """Test loading when Credential Manager access fails."""
    with patch('polychat.keys.backends.keyring') as mock_keyring:
        mock_keyring.get_password.side_effect = Exception("Access denied")

        with pytest.raises(ValueError, match="Failed to access"):
            load_from_credential_manager("polychat", "test-account")


def test_store_in_credential_manager_success():
    """Test storing API key in Windows Credential Manager."""
    with patch('polychat.keys.backends.keyring') as mock_keyring:
        store_in_credential_manager("polychat", "test-account", "sk-new-key")

        mock_keyring.set_password.assert_called_once_with(
            "polychat", "test-account", "sk-new-key"
        )


def test_store_in_credential_manager_not_installed():
    """Test storing when keyring package not installed."""
    with patch('polychat.keys.backends.keyring', None):
        with pytest.raises(ImportError, match="keyring package not installed"):
            store_in_credential_manager("polychat", "test-account", "sk-key")


def test_store_in_credential_manager_failure():
    """Test storing when operation fails."""
    with patch('polychat.keys.backends.keyring') as mock_keyring:
        mock_keyring.set_password.side_effect = Exception("Write failed")

        with pytest.raises(ValueError, match="Failed to store key in"):
            store_in_credential_manager("polychat", "test-account", "sk-key")
