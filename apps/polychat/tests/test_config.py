"""Tests for app-config loading and validation."""

import json

import pytest

from polychat.config import (
    AppConfigStartupError,
    create_config,
    load_config,
    load_or_create_startup_config,
    validate_config,
)


def test_load_config_nonexistent(tmp_path):
    """Loading a missing app config should raise FileNotFoundError."""
    config_path = tmp_path / "missing-config.json"

    with pytest.raises(FileNotFoundError, match="App config not found"):
        load_config(str(config_path))


def test_load_config_invalid_json(tmp_path):
    """Malformed app-config JSON should raise JSONDecodeError."""
    config_path = tmp_path / "invalid-config.json"
    config_path.write_text("{ invalid json }", encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        load_config(str(config_path))


def test_load_config_valid(tmp_path):
    """A valid app config should deserialize to the typed model."""
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "sound_notifications": {
                    "enabled": True,
                    "sound": "Tink",
                    "volume": 0.5,
                },
                "text_colors": {
                    "user_input": "ansigreen",
                    "cost_line": "ansiblue",
                },
            }
        ),
        encoding="utf-8",
    )

    config = load_config(str(config_path))

    assert config.sound_notifications is not None
    assert config.sound_notifications.enabled is True
    assert config.sound_notifications.sound == "Tink"
    assert config.sound_notifications.volume == 0.5
    assert config.text_colors is not None
    assert config.text_colors.user_input == "ansigreen"
    assert config.text_colors.cost_line == "ansiblue"


def test_validate_config_rejects_invalid_sound_notification_value():
    """Known config keys should fail fast on wrong types."""
    config = {
        "sound_notifications": {
            "enabled": "yes",
        }
    }

    with pytest.raises(
        ValueError,
        match="'sound_notifications.enabled' must be a boolean or null",
    ):
        validate_config(config)


def test_validate_config_rejects_invalid_text_color_value():
    """Text-color entries must be strings or null."""
    config = {
        "text_colors": {
            "user_input": 123,
        }
    }

    with pytest.raises(
        ValueError,
        match="'text_colors.user_input' must be a string or null",
    ):
        validate_config(config)


def test_validate_config_rejects_invalid_sound_name_type():
    config = {
        "sound_notifications": {
            "sound": 123,
        }
    }

    with pytest.raises(
        ValueError,
        match="'sound_notifications.sound' must be a string or null",
    ):
        validate_config(config)


def test_validate_config_rejects_invalid_sound_volume():
    config = {
        "sound_notifications": {
            "volume": 1.5,
        }
    }

    with pytest.raises(
        ValueError,
        match="'sound_notifications.volume' must be between 0 and 1",
    ):
        validate_config(config)


def test_create_config_writes_template_sections(tmp_path):
    """Creating the first-run config should write the expected sections."""
    config_path = tmp_path / "config.json"

    created_config, messages = create_config(str(config_path))

    assert messages == [f"Created app config: {config_path.resolve()}"]
    assert created_config["sound_notifications"] == {
        "enabled": None,
        "sound": None,
        "volume": None,
    }
    assert created_config["text_colors"] == {
        "user_input": None,
        "cost_line": None,
    }
    assert json.loads(config_path.read_text(encoding="utf-8")) == created_config


def test_load_or_create_startup_config_creates_missing_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
):
    config_path = tmp_path / "config.json"
    monkeypatch.setattr(
        "polychat.config.startup.default_config_path",
        lambda: str(config_path),
    )

    startup_config = load_or_create_startup_config()

    assert config_path.exists()
    assert startup_config.path == str(config_path)
    assert startup_config.messages == [f"Created app config: {config_path.resolve()}"]
    assert startup_config.config.text_colors is not None


def test_load_or_create_startup_config_raises_clean_error_for_invalid_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
):
    config_path = tmp_path / "config.json"
    config_path.write_text("{ invalid json }", encoding="utf-8")
    monkeypatch.setattr(
        "polychat.config.startup.default_config_path",
        lambda: str(config_path),
    )

    with pytest.raises(
        AppConfigStartupError,
        match="App config file is invalid",
    ):
        load_or_create_startup_config()
