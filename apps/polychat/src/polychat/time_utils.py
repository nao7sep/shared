"""Shared date/time utilities used across the application."""

from __future__ import annotations

from datetime import datetime, timezone


def utc_now_iso() -> str:
    """Return a high-precision UTC timestamp with explicit ``Z`` marker.

    Format: ``2026-01-15T12:34:56.789012Z``
    """
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


def parse_utc_to_local(timestamp: str, fmt: str) -> str | None:
    """Parse a Z-suffixed ISO timestamp and format it as local time.

    Returns the formatted string, or ``None`` when *timestamp* is
    unparseable so callers can supply their own fallback.
    """
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone().strftime(fmt)
    except (ValueError, TypeError, AttributeError):
        return None
