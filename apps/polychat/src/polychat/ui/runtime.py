"""UI runtime preparation from validated app config."""

from __future__ import annotations

from dataclasses import dataclass

from ..domain.config import AppConfig
from .notifications import NotificationPlayer, create_notification_player
from .theme import validate_interactive_style


@dataclass(slots=True)
class UiRuntime:
    """Prepared UI runtime dependencies for one app session."""

    notification_player: NotificationPlayer


def prepare_ui_runtime(app_config: AppConfig) -> UiRuntime:
    """Validate UI-related config and build runtime UI dependencies."""
    validate_interactive_style(app_config)
    return UiRuntime(notification_player=create_notification_player(app_config))
