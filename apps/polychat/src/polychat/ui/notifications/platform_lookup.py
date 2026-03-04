"""Platform-specific notification sound lookup helpers."""

from __future__ import annotations

import os
from pathlib import Path

_MACOS_SYSTEM_SOUND_EXTENSIONS = (".aiff", ".caf", ".wav")
_LINUX_SYSTEM_SOUND_DIRECTORIES = (
    "/usr/share/sounds/freedesktop/stereo",
    "/usr/local/share/sounds/freedesktop/stereo",
    "/usr/share/sounds",
    "/usr/local/share/sounds",
)
_LINUX_SYSTEM_SOUND_EXTENSIONS = (".oga", ".ogg", ".wav")


def resolve_system_sound_path(token: str, *, platform: str) -> str | None:
    """Resolve a system sound token to a concrete sound file path."""
    if platform == "darwin":
        return _resolve_macos_system_sound_path(token)
    if platform == "win32":
        return _resolve_windows_system_sound_path(token)
    return _resolve_linux_system_sound_path(token)


def _resolve_macos_system_sound_path(token: str) -> str | None:
    """Resolve one macOS system sound token."""
    for extension in _MACOS_SYSTEM_SOUND_EXTENSIONS:
        candidate = Path("/System/Library/Sounds") / f"{token}{extension}"
        if candidate.is_file():
            return str(candidate.resolve())
    return None


def _resolve_windows_system_sound_path(token: str) -> str | None:
    """Resolve one Windows system sound alias to its configured WAV file."""
    registry_candidate = _resolve_windows_registry_sound_path(token)
    if registry_candidate is not None:
        return registry_candidate

    windir = os.environ.get("WINDIR")
    if not windir:
        return None

    candidate = Path(windir) / "Media" / f"{token}.wav"
    if candidate.is_file():
        return str(candidate.resolve())
    return None


def _resolve_windows_registry_sound_path(token: str) -> str | None:
    """Read the current user's Windows sound scheme path for one alias."""
    try:
        import winreg
    except ImportError:
        return None

    for suffix in (".Current", ".Default"):
        subkey = rf"AppEvents\Schemes\Apps\.Default\{token}\{suffix}"
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, subkey) as key:
                value, _value_type = winreg.QueryValueEx(key, None)
        except OSError:
            continue
        if not isinstance(value, str) or not value.strip():
            continue
        candidate = Path(os.path.expandvars(value.strip()))
        if candidate.is_file():
            return str(candidate.resolve())
    return None


def _resolve_linux_system_sound_path(token: str) -> str | None:
    """Resolve one Linux system sound token from common shared sound dirs."""
    for directory in _LINUX_SYSTEM_SOUND_DIRECTORIES:
        for extension in _LINUX_SYSTEM_SOUND_EXTENSIONS:
            candidate = Path(directory) / f"{token}{extension}"
            if candidate.is_file():
                return str(candidate.resolve())
    return None
