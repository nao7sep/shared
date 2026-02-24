"""Shared provider log-message helpers."""

from __future__ import annotations

import logging

from ..logging import log_event


def log_provider_error(provider: str, message: str) -> None:
    """Emit a standardized provider error log event."""
    log_event(
        "provider_log",
        level=logging.ERROR,
        provider=provider,
        message=message,
    )


def authentication_failed_message(error: Exception) -> str:
    """Build the standard authentication-failure message."""
    return f"Authentication failed: {error}"


def bad_request_message(error: Exception, *, detail: str | None = None) -> str:
    """Build provider bad-request message with optional detail hint."""
    if detail:
        return f"Bad request ({detail}): {error}"
    return f"Bad request: {error}"


def api_error_after_retries_message(error: Exception) -> str:
    """Build standardized retry-exhausted API error message."""
    return f"API error after retries: {type(error).__name__}: {error}"


def unexpected_error_message(error: Exception) -> str:
    """Build standardized unexpected-error message."""
    return f"Unexpected error: {type(error).__name__}: {error}"
