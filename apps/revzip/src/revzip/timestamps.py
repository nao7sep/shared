"""Timestamp formatting/parsing helpers."""

from __future__ import annotations

from datetime import datetime, timezone

_UTC_TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
_LOCAL_DISPLAY_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
_LOCAL_FILENAME_TIMESTAMP_FORMAT = "%Y-%m-%d_%H-%M-%S"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def format_created_utc(created_utc_dt: datetime) -> str:
    utc_dt = _coerce_to_utc(created_utc_dt)
    return utc_dt.strftime(_UTC_TIMESTAMP_FORMAT)


def parse_created_utc(created_utc: str) -> datetime:
    parsed = datetime.strptime(created_utc, _UTC_TIMESTAMP_FORMAT)
    return parsed.replace(tzinfo=timezone.utc)


def parse_created_at(created_at: str) -> datetime:
    return datetime.strptime(created_at, _LOCAL_DISPLAY_TIMESTAMP_FORMAT)


def format_created_at(created_utc_dt: datetime) -> str:
    utc_dt = _coerce_to_utc(created_utc_dt)
    return utc_dt.astimezone().strftime(_LOCAL_DISPLAY_TIMESTAMP_FORMAT)


def format_filename_timestamp(created_utc_dt: datetime) -> str:
    utc_dt = _coerce_to_utc(created_utc_dt)
    return utc_dt.astimezone().strftime(_LOCAL_FILENAME_TIMESTAMP_FORMAT)


def _coerce_to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("UTC datetime value must be timezone-aware.")
    return value.astimezone(timezone.utc)
