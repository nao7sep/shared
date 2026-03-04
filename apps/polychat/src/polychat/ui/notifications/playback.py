"""Notification sound playback backends and startup probing."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import wave
from pathlib import Path
from typing import Any

from ...domain.config import AppConfig
from .contracts import (
    NoOpNotificationPlayer,
    NotificationPlayer,
    ResolvedNotificationSound,
)
from .resolution import resolve_notification_sound

_SOUND_PROBE_TIMEOUT_SECONDS = 0.25


class WinsoundNotificationPlayer:
    """Windows notification player backed by the standard winsound module."""

    def __init__(self, winsound_module: Any, sound: ResolvedNotificationSound) -> None:
        self._winsound = winsound_module
        self._sound = sound
        self._flags = (
            self._winsound.SND_ASYNC
            | self._winsound.SND_FILENAME
            | self._winsound.SND_NODEFAULT
        )

    def notify(self) -> None:
        """Play the configured notification sound asynchronously."""
        try:
            self._winsound.PlaySound(self._sound.path, self._flags)
        except Exception:
            logging.warning(
                "Notification playback failed (platform=win32, sound=%s)",
                self._sound.path,
                exc_info=True,
            )


class SubprocessNotificationPlayer:
    """Notification player backed by one OS command invocation."""

    def __init__(
        self,
        *,
        command: list[str],
        sound: ResolvedNotificationSound,
        volume_args: list[str],
    ) -> None:
        self._command = list(command)
        self._sound = sound
        self._volume_args = list(volume_args)

    def notify(self) -> None:
        """Spawn the backend command without blocking the REPL."""
        try:
            subprocess.Popen(
                [
                    *self._command,
                    *self._volume_args,
                    self._sound.path,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            logging.warning(
                "Notification playback failed (sound=%s, command=%s)",
                self._sound.path,
                self._command,
                exc_info=True,
            )


def create_notification_player(
    app_config: AppConfig,
    *,
    platform: str | None = None,
) -> NotificationPlayer:
    """Resolve configured sound once and build the matching runtime player."""
    resolved_sound = resolve_notification_sound(
        app_config,
        platform=platform,
    )
    if resolved_sound is None:
        return NoOpNotificationPlayer()

    resolved_platform = platform or os.sys.platform
    if resolved_platform == "win32":
        _validate_windows_backend_support(resolved_sound.path)
        return WinsoundNotificationPlayer(_load_winsound(), resolved_sound)
    if resolved_platform == "darwin":
        if not shutil.which("afplay"):
            raise ValueError("macOS sound notifications require 'afplay'")
        _probe_subprocess_sound(
            ["afplay", "-v", "0", "-t", "0.01", resolved_sound.path],
            backend_name="afplay",
        )
        return SubprocessNotificationPlayer(
            command=["afplay"],
            sound=resolved_sound,
            volume_args=["-v", str(resolved_sound.volume)],
        )

    linux_command, linux_volume_args = _resolve_linux_command(resolved_sound.volume)
    _probe_subprocess_sound(
        _build_linux_probe_command(resolved_sound.path),
        backend_name=linux_command[0],
    )
    return SubprocessNotificationPlayer(
        command=linux_command,
        sound=resolved_sound,
        volume_args=linux_volume_args,
    )


def _load_winsound() -> Any:
    """Import winsound only when Windows notifications are enabled."""
    try:
        import winsound
    except Exception as e:
        raise ValueError(
            "Windows sound notifications require the standard 'winsound' module"
        ) from e
    return winsound


def _resolve_linux_command(volume: float) -> tuple[list[str], list[str]]:
    """Choose one Linux sound backend command with volume support."""
    if shutil.which("paplay"):
        return ["paplay"], [f"--volume={max(0, int(volume * 65536))}"]
    if shutil.which("ffplay"):
        return (
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"],
            ["-volume", str(max(0, min(100, round(volume * 100))))],
        )
    raise ValueError(
        "Linux sound notifications require 'paplay' or 'ffplay' to be available"
    )


def _validate_windows_backend_support(path: str) -> None:
    """Validate the Windows backend preconditions for the resolved file."""
    if Path(path).suffix.lower() != ".wav":
        raise ValueError("Windows sound notifications currently require a .wav file")
    try:
        with wave.open(path, "rb") as wave_file:
            wave_file.getparams()
    except (wave.Error, EOFError) as e:
        raise ValueError(
            f"Windows notification sound is not a valid WAV file: {path}: {e}"
        ) from e


def _build_linux_probe_command(path: str) -> list[str]:
    """Build the Linux probe command for the active backend."""
    if shutil.which("paplay"):
        return ["paplay", "--volume=0", path]
    if shutil.which("ffplay"):
        return [
            "ffplay",
            "-nodisp",
            "-autoexit",
            "-loglevel",
            "error",
            "-volume",
            "0",
            "-t",
            "0.01",
            path,
        ]
    raise ValueError(
        "Linux sound notifications require 'paplay' or 'ffplay' to be available"
    )


def _probe_subprocess_sound(command: list[str], *, backend_name: str) -> None:
    """Probe one backend at startup so broken sound config fails fast."""
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=_SOUND_PROBE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return
    except OSError as e:
        raise ValueError(
            f"Could not start notification backend '{backend_name}': {e}"
        ) from e

    if result.returncode == 0:
        return

    error_output = (result.stderr or "").strip()
    if error_output:
        raise ValueError(
            f"Notification sound is not playable with {backend_name}: {error_output}"
        )
    raise ValueError(f"Notification sound is not playable with {backend_name}")
