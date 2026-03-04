"""Tests for notification sound resolution and startup player creation."""

from __future__ import annotations

import wave
from pathlib import Path

import pytest

from polychat.ui.notifications import (
    NoOpNotificationPlayer,
    create_notification_player,
    resolve_notification_sound,
)
from test_helpers import make_app_config


def _write_wave_file(path: Path) -> None:
    """Write a minimal valid WAV file for notification tests."""
    with wave.open(str(path), "wb") as wave_file:
        wave_file.setnchannels(1)
        wave_file.setsampwidth(2)
        wave_file.setframerate(8000)
        wave_file.writeframes(b"\x00\x00" * 8)


class _FakeWinsound:
    SND_ASYNC = 1
    SND_FILENAME = 2
    SND_NODEFAULT = 4

    def __init__(self) -> None:
        self.calls: list[tuple[str, int]] = []

    def PlaySound(self, path: str, flags: int) -> None:
        self.calls.append((path, flags))


def test_resolve_notification_sound_returns_none_when_disabled(tmp_path):
    app_config = make_app_config(
        sound_notifications={
            "enabled": False,
            "sound": None,
            "volume": None,
        }
    )

    resolved = resolve_notification_sound(
        app_config,
    )

    assert resolved is None


def test_resolve_notification_sound_uses_absolute_file_path(tmp_path):
    sound_path = tmp_path / "notify.wav"
    _write_wave_file(sound_path)
    app_config = make_app_config(
        sound_notifications={
            "enabled": True,
            "sound": str(sound_path),
            "volume": 0.4,
        }
    )

    resolved = resolve_notification_sound(
        app_config,
    )

    assert resolved is not None
    assert resolved.path == str(sound_path.resolve())
    assert resolved.volume == 0.4


def test_resolve_notification_sound_rejects_plain_relative_path(tmp_path):
    app_config = make_app_config(
        sound_notifications={
            "enabled": True,
            "sound": "notify.wav",
            "volume": 1.0,
        }
    )

    with pytest.raises(
        ValueError,
        match="Relative paths without prefix are not supported",
    ):
        resolve_notification_sound(
            app_config,
        )


def test_resolve_notification_sound_rejects_invalid_system_token(tmp_path):
    app_config = make_app_config(
        sound_notifications={
            "enabled": True,
            "sound": "Tink?",
            "volume": 1.0,
        }
    )

    with pytest.raises(
        ValueError,
        match="not a valid system sound token",
    ):
        resolve_notification_sound(
            app_config,
        )


def test_create_notification_player_returns_noop_when_disabled(tmp_path):
    player = create_notification_player(
        make_app_config(
            sound_notifications={
                "enabled": False,
                "sound": None,
                "volume": None,
            }
        ),
    )

    assert isinstance(player, NoOpNotificationPlayer)


def test_resolve_notification_sound_uses_platform_default_when_sound_is_missing(
    monkeypatch: pytest.MonkeyPatch,
):
    app_config = make_app_config(
        sound_notifications={
            "enabled": None,
            "sound": None,
            "volume": None,
        }
    )
    monkeypatch.setattr(
        "polychat.ui.notifications.resolution.resolve_system_sound_path",
        lambda token, *, platform: (
            "/System/Library/Sounds/Tink.aiff" if token == "Tink" else None
        ),
    )

    resolved = resolve_notification_sound(
        app_config,
        platform="darwin",
    )

    assert resolved is not None
    assert resolved.path == "/System/Library/Sounds/Tink.aiff"
    assert resolved.volume == 1.0


def test_resolve_notification_sound_raises_when_no_platform_default_is_available(
    monkeypatch: pytest.MonkeyPatch,
):
    app_config = make_app_config(
        sound_notifications={
            "enabled": None,
            "sound": None,
            "volume": None,
        }
    )
    monkeypatch.setattr(
        "polychat.ui.notifications.resolution.resolve_system_sound_path",
        lambda token, *, platform: None,
    )

    with pytest.raises(
        ValueError,
        match="no default notification sound is available",
    ):
        resolve_notification_sound(
            app_config,
            platform="darwin",
        )


def test_create_notification_player_builds_windows_player_once(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    sound_path = tmp_path / "notify.wav"
    _write_wave_file(sound_path)
    app_config = make_app_config(
        sound_notifications={
            "enabled": True,
            "sound": str(sound_path),
            "volume": 0.25,
        }
    )
    fake_winsound = _FakeWinsound()
    monkeypatch.setattr(
        "polychat.ui.notifications.playback._load_winsound",
        lambda: fake_winsound,
    )

    player = create_notification_player(
        app_config,
        platform="win32",
    )
    player.notify()

    assert fake_winsound.calls == [
        (
            str(sound_path.resolve()),
            fake_winsound.SND_ASYNC
            | fake_winsound.SND_FILENAME
            | fake_winsound.SND_NODEFAULT,
        )
    ]


def test_create_notification_player_rejects_invalid_windows_wave_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    sound_path = tmp_path / "notify.wav"
    sound_path.write_bytes(b"not-a-wave-file")
    app_config = make_app_config(
        sound_notifications={
            "enabled": True,
            "sound": str(sound_path),
            "volume": 1.0,
        }
    )
    monkeypatch.setattr(
        "polychat.ui.notifications.playback._load_winsound",
        lambda: _FakeWinsound(),
    )

    with pytest.raises(
        ValueError,
        match="not a valid WAV file",
    ):
        create_notification_player(
            app_config,
            platform="win32",
        )


def test_create_notification_player_rejects_unplayable_macos_sound(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    sound_path = tmp_path / "notify.caf"
    sound_path.write_bytes(b"not-a-real-audio-file")
    app_config = make_app_config(
        sound_notifications={
            "enabled": True,
            "sound": str(sound_path),
            "volume": 1.0,
        }
    )
    monkeypatch.setattr(
        "polychat.ui.notifications.playback.shutil.which",
        lambda name: "/usr/bin/afplay" if name == "afplay" else None,
    )

    def _raise_probe_error(command: list[str], *, backend_name: str) -> None:
        raise ValueError(
            f"Notification sound is not playable with {backend_name}: bad file"
        )

    monkeypatch.setattr(
        "polychat.ui.notifications.playback._probe_subprocess_sound",
        _raise_probe_error,
    )

    with pytest.raises(
        ValueError,
        match="Notification sound is not playable with afplay: bad file",
    ):
        create_notification_player(
            app_config,
            platform="darwin",
        )
