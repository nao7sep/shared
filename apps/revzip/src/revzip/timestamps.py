"""Timestamp formatting/parsing helpers."""

from __future__ import annotations

from datetime import datetime, timezone

from .constants import (
    LOCAL_DISPLAY_TIMESTAMP_FORMAT,
    LOCAL_FILENAME_TIMESTAMP_FORMAT,
    UTC_TIMESTAMP_FORMAT,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def format_created_utc(created_utc_dt: datetime) -> str:
    utc_dt = _coerce_to_utc(created_utc_dt)
    return utc_dt.strftime(UTC_TIMESTAMP_FORMAT)


def parse_created_utc(created_utc: str) -> datetime:
    parsed = datetime.strptime(created_utc, UTC_TIMESTAMP_FORMAT)
    return parsed.replace(tzinfo=timezone.utc)


def format_created_at(created_utc_dt: datetime) -> str:
    utc_dt = _coerce_to_utc(created_utc_dt)
    return utc_dt.astimezone().strftime(LOCAL_DISPLAY_TIMESTAMP_FORMAT)


def format_filename_timestamp(created_utc_dt: datetime) -> str:
    utc_dt = _coerce_to_utc(created_utc_dt)
    return utc_dt.astimezone().strftime(LOCAL_FILENAME_TIMESTAMP_FORMAT)


def _coerce_to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("UTC datetime value must be timezone-aware.")
    return value.astimezone(timezone.utc)
