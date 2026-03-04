"""Public notification sound API."""

from .contracts import (
    NoOpNotificationPlayer,
    NotificationPlayer,
    ResolvedNotificationSound,
)
from .playback import create_notification_player
from .resolution import (
    DEFAULT_NOTIFICATION_VOLUME,
    DEFAULT_SOUND_NOTIFICATIONS_ENABLED,
    resolve_notification_sound,
)

__all__ = [
    "DEFAULT_NOTIFICATION_VOLUME",
    "DEFAULT_SOUND_NOTIFICATIONS_ENABLED",
    "NoOpNotificationPlayer",
    "NotificationPlayer",
    "ResolvedNotificationSound",
    "create_notification_player",
    "resolve_notification_sound",
]
