"""Cross-platform sound notification helper."""

from __future__ import annotations

import functools
import subprocess
import sys
from pathlib import Path
from typing import Optional

from ..config import load_config
from ..path_utils import map_path


def _try_resolve_path(raw: str) -> Optional[str]:
    """Resolve a path string via map_path(); return None on any failure."""
    try:
        return map_path(raw)
    except Exception:
        return None


@functools.lru_cache(maxsize=1)
def _get_resolved_sound() -> Optional[str]:
    """Resolve the platform sound setting once and cache the result.

    Returns the resolved file path, alias name (Windows), or None if sound
    is disabled or the configured value cannot be resolved to a usable sound.
    """
    cfg = load_config().notifications
    if not cfg.sound:
        return None

    if sys.platform == "darwin":
        raw = cfg.macos_sound
        if not raw:
            return None
        resolved = _try_resolve_path(raw)
        if resolved and Path(resolved).is_file():
            return resolved
        system_path = f"/System/Library/Sounds/{raw}.aiff"
        if Path(system_path).is_file():
            return system_path
        return None

    elif sys.platform == "win32":
        raw = cfg.windows_sound
        if not raw:
            return None
        resolved = _try_resolve_path(raw)
        if resolved and Path(resolved).is_file():
            return resolved
        # Fall back to treating the value as a Windows sound alias name.
        return raw

    else:
        raw = cfg.linux_sound
        if not raw:
            return None
        resolved = _try_resolve_path(raw)
        if resolved and Path(resolved).is_file():
            return resolved
        return None


def notify() -> None:
    """Play the configured notification sound. Silently no-ops on any failure."""
    try:
        cfg = load_config().notifications
        sound = _get_resolved_sound()
        if sound is None:
            return

        if sys.platform == "darwin":
            subprocess.run(
                ["afplay", "-v", str(cfg.volume), sound],
                capture_output=True,
                timeout=5,
            )

        elif sys.platform == "win32":
            import winsound
            if Path(sound).is_file():
                winsound.PlaySound(sound, winsound.SND_FILENAME | winsound.SND_ASYNC)
            else:
                winsound.PlaySound(sound, winsound.SND_ALIAS | winsound.SND_ASYNC)

        else:
            subprocess.run(
                ["paplay", f"--volume={int(cfg.volume * 65536)}", sound],
                capture_output=True,
                timeout=5,
            )

    except Exception:
        pass
