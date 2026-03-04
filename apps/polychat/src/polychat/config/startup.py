"""App-config startup loading helpers."""

from __future__ import annotations

from dataclasses import dataclass

from ..domain.config import AppConfig
from .files import create_config, default_config_path, load_config


class AppConfigStartupError(Exception):
    """Raised when app-config startup preparation cannot continue."""


@dataclass(slots=True)
class StartupAppConfig:
    """Loaded startup app-config plus startup messages."""

    config: AppConfig
    path: str
    messages: list[str]


def load_or_create_startup_config() -> StartupAppConfig:
    """Load app config for startup, creating the file on first run."""
    config_path = default_config_path()

    try:
        return StartupAppConfig(
            config=load_config(config_path),
            path=config_path,
            messages=[],
        )
    except FileNotFoundError:
        try:
            _created_config, messages = create_config(config_path)
        except OSError as e:
            raise AppConfigStartupError(
                f"Could not create app config file {config_path}: {e}"
            ) from e
        except ValueError as e:
            raise AppConfigStartupError(
                f"Could not create app config file {config_path}: {e}"
            ) from e

        try:
            return StartupAppConfig(
                config=load_config(config_path),
                path=config_path,
                messages=messages,
            )
        except OSError as e:
            raise AppConfigStartupError(
                f"Could not read app config file {config_path}: {e}"
            ) from e
        except ValueError as e:
            raise AppConfigStartupError(
                f"App config file is invalid: {config_path}: {e}"
            ) from e
    except OSError as e:
        raise AppConfigStartupError(
            f"Could not read app config file {config_path}: {e}"
        ) from e
    except ValueError as e:
        raise AppConfigStartupError(
            f"App config file is invalid: {config_path}: {e}"
        ) from e
