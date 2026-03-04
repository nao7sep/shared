"""Notification sound runtime contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ResolvedNotificationSound:
    """Resolved notification sound path and volume."""

    path: str
    volume: float


class NotificationPlayer(Protocol):
    """Minimal runtime contract for notification playback."""

    def notify(self) -> None:
        """Play one notification sound, or no-op when disabled."""


class NoOpNotificationPlayer:
    """Notification player used when sound notifications are disabled."""

    def notify(self) -> None:
        """Do nothing."""
