"""Tests for pydeli.state_store module."""


import pytest

from pydeli.models import Registry, TokenScope
from pydeli.state_store import (
    delete_credential,
    load_credential,
    save_credential,
    update_credential_token,
)
from pydeli.models import CredentialState


@pytest.fixture(autouse=True)
def _patch_state_dir(tmp_path, monkeypatch):
    """Redirect state directory to a temp location."""
    monkeypatch.setattr("pydeli.state_store._state_dir", lambda: tmp_path)


class TestStateStore:
    def test_load_nonexistent_returns_none(self):
        result = load_credential(Registry.TESTPYPI, "myproject")
        assert result is None

    def test_save_and_load(self):
        from datetime import datetime, timezone

        cred = CredentialState(
            registry=Registry.TESTPYPI,
            project_name="myproject",
            token_value="pypi-test-token",
            token_scope=TokenScope.PROJECT,
            needs_rotation=False,
            created_utc=datetime.now(timezone.utc),
            updated_utc=datetime.now(timezone.utc),
        )
        save_credential(cred)
        loaded = load_credential(Registry.TESTPYPI, "myproject")
        assert loaded is not None
        assert loaded.project_name == "myproject"
        assert loaded.token_value == "pypi-test-token"
        assert loaded.token_scope == TokenScope.PROJECT
        assert loaded.needs_rotation is False

    def test_update_credential_token_new(self):
        cred = update_credential_token(
            Registry.PYPI, "newproject", "pypi-new-token",
            scope=TokenScope.ACCOUNT, needs_rotation=True,
        )
        assert cred.token_value == "pypi-new-token"
        assert cred.needs_rotation is True

        loaded = load_credential(Registry.PYPI, "newproject")
        assert loaded is not None
        assert loaded.token_value == "pypi-new-token"

    def test_update_credential_token_existing(self):
        update_credential_token(
            Registry.TESTPYPI, "proj", "old-token",
            scope=TokenScope.ACCOUNT, needs_rotation=True,
        )
        updated = update_credential_token(
            Registry.TESTPYPI, "proj", "new-token",
            scope=TokenScope.PROJECT, needs_rotation=False,
        )
        assert updated.token_value == "new-token"
        assert updated.token_scope == TokenScope.PROJECT
        assert updated.needs_rotation is False

    def test_delete_credential(self):
        update_credential_token(
            Registry.TESTPYPI, "delme", "token",
            scope=TokenScope.PROJECT, needs_rotation=False,
        )
        assert load_credential(Registry.TESTPYPI, "delme") is not None
        delete_credential(Registry.TESTPYPI, "delme")
        assert load_credential(Registry.TESTPYPI, "delme") is None

    def test_delete_nonexistent_is_noop(self):
        # Should not raise
        delete_credential(Registry.PYPI, "nonexistent")

    def test_separate_registry_credentials(self):
        update_credential_token(
            Registry.TESTPYPI, "proj", "test-token",
            scope=TokenScope.ACCOUNT, needs_rotation=True,
        )
        update_credential_token(
            Registry.PYPI, "proj", "prod-token",
            scope=TokenScope.PROJECT, needs_rotation=False,
        )
        test_cred = load_credential(Registry.TESTPYPI, "proj")
        prod_cred = load_credential(Registry.PYPI, "proj")
        assert test_cred is not None
        assert prod_cred is not None
        assert test_cred.token_value == "test-token"
        assert prod_cred.token_value == "prod-token"
