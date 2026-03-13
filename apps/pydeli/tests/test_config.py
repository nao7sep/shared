from __future__ import annotations

import pytest

from pydeli.config import get_token, load_config, save_config, set_token
from pydeli.errors import ConfigError
from pydeli.models import RegistryTarget


class TestGetToken:
    """Token retrieval from config dicts."""

    def test_returns_token_when_present(self) -> None:
        config = {"tokens": {"myapp": {"testpypi": "pypi-abc123"}}}
        assert get_token(config, "myapp", RegistryTarget.TESTPYPI) == "pypi-abc123"

    def test_returns_none_for_missing_app(self) -> None:
        config = {"tokens": {}}
        assert get_token(config, "myapp", RegistryTarget.PYPI) is None

    def test_returns_none_for_missing_registry(self) -> None:
        config = {"tokens": {"myapp": {"testpypi": "pypi-abc"}}}
        assert get_token(config, "myapp", RegistryTarget.PYPI) is None

    def test_returns_none_for_empty_string_token(self) -> None:
        """An empty string token is treated as missing."""
        config = {"tokens": {"myapp": {"pypi": ""}}}
        assert get_token(config, "myapp", RegistryTarget.PYPI) is None

    def test_returns_none_for_non_string_token(self) -> None:
        """A numeric or None token is treated as missing."""
        config = {"tokens": {"myapp": {"pypi": 12345}}}
        assert get_token(config, "myapp", RegistryTarget.PYPI) is None

    def test_handles_missing_tokens_section(self) -> None:
        """Config with no 'tokens' key at all."""
        config = {}
        assert get_token(config, "myapp", RegistryTarget.PYPI) is None


class TestSetToken:
    """Token insertion into config dicts."""

    def test_sets_new_token_for_new_app(self) -> None:
        config: dict = {"tokens": {}}
        set_token(config, "myapp", RegistryTarget.PYPI, "pypi-new")
        assert config["tokens"]["myapp"]["pypi"] == "pypi-new"

    def test_overwrites_existing_token(self) -> None:
        config = {"tokens": {"myapp": {"pypi": "pypi-old"}}}
        set_token(config, "myapp", RegistryTarget.PYPI, "pypi-replaced")
        assert config["tokens"]["myapp"]["pypi"] == "pypi-replaced"

    def test_preserves_other_registry_tokens(self) -> None:
        """Setting a PyPI token should not touch the TestPyPI token."""
        config = {"tokens": {"myapp": {"testpypi": "pypi-test"}}}
        set_token(config, "myapp", RegistryTarget.PYPI, "pypi-prod")
        assert config["tokens"]["myapp"]["testpypi"] == "pypi-test"
        assert config["tokens"]["myapp"]["pypi"] == "pypi-prod"

    def test_creates_tokens_section_if_missing(self) -> None:
        config: dict = {}
        set_token(config, "myapp", RegistryTarget.TESTPYPI, "tok")
        assert config["tokens"]["myapp"]["testpypi"] == "tok"


class TestLoadSaveConfig:
    """Round-trip persistence of config.json via monkeypatched paths."""

    def test_roundtrip(self, tmp_path: pytest.TempPathFactory, monkeypatch) -> None:
        """Save then load should preserve all data."""
        config_dir = tmp_path / ".pydeli"
        config_path = config_dir / "config.json"

        monkeypatch.setattr("pydeli.config.CONFIG_DIR", config_dir)
        monkeypatch.setattr("pydeli.config.CONFIG_PATH", config_path)

        original = {"tokens": {"app1": {"pypi": "tok1", "testpypi": "tok2"}}}
        save_config(original)
        loaded = load_config()

        assert loaded["tokens"]["app1"]["pypi"] == "tok1"
        assert loaded["tokens"]["app1"]["testpypi"] == "tok2"

    def test_auto_creates_on_first_load(
        self, tmp_path: pytest.TempPathFactory, monkeypatch
    ) -> None:
        """First load should create the file and return empty config."""
        config_dir = tmp_path / ".pydeli"
        config_path = config_dir / "config.json"

        monkeypatch.setattr("pydeli.config.CONFIG_DIR", config_dir)
        monkeypatch.setattr("pydeli.config.CONFIG_PATH", config_path)

        config = load_config()
        assert config_path.exists()
        assert config["tokens"] == {}

    def test_corrupt_json_raises(
        self, tmp_path: pytest.TempPathFactory, monkeypatch
    ) -> None:
        """Corrupt JSON should raise ConfigError, not crash."""
        config_dir = tmp_path / ".pydeli"
        config_dir.mkdir()
        config_path = config_dir / "config.json"
        config_path.write_text("not json {{{", encoding="utf-8")

        monkeypatch.setattr("pydeli.config.CONFIG_DIR", config_dir)
        monkeypatch.setattr("pydeli.config.CONFIG_PATH", config_path)

        with pytest.raises(ConfigError, match="Failed to read config file"):
            load_config()

    def test_non_dict_json_raises(
        self, tmp_path: pytest.TempPathFactory, monkeypatch
    ) -> None:
        """A JSON array instead of object should raise ConfigError."""
        config_dir = tmp_path / ".pydeli"
        config_dir.mkdir()
        config_path = config_dir / "config.json"
        config_path.write_text("[1, 2, 3]", encoding="utf-8")

        monkeypatch.setattr("pydeli.config.CONFIG_DIR", config_dir)
        monkeypatch.setattr("pydeli.config.CONFIG_PATH", config_path)

        with pytest.raises(ConfigError, match="must contain a JSON object"):
            load_config()

    def test_load_adds_tokens_key_if_missing(
        self, tmp_path: pytest.TempPathFactory, monkeypatch
    ) -> None:
        """A valid JSON object missing 'tokens' should get it added."""
        config_dir = tmp_path / ".pydeli"
        config_dir.mkdir()
        config_path = config_dir / "config.json"
        config_path.write_text('{"other": "data"}', encoding="utf-8")

        monkeypatch.setattr("pydeli.config.CONFIG_DIR", config_dir)
        monkeypatch.setattr("pydeli.config.CONFIG_PATH", config_path)

        config = load_config()
        assert config["tokens"] == {}
        assert config["other"] == "data"
