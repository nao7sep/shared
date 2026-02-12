"""Centralized timeout policy and helpers."""

from __future__ import annotations

import math
from typing import Any, Mapping

import httpx


# Profile-level timeout defaults and mode behavior.
DEFAULT_PROFILE_TIMEOUT_SEC = 30
AI_MODE_TIMEOUT_MULTIPLIER = 3

# Shared provider HTTP timeout buckets.
AI_HTTP_CONNECT_TIMEOUT_SEC = 10.0
AI_HTTP_WRITE_TIMEOUT_SEC = 15.0
AI_HTTP_POOL_TIMEOUT_SEC = 5.0

# Citation redirect resolution timeout.
CITATION_REDIRECT_RESOLVE_TIMEOUT_SEC = 5.0
CITATION_REDIRECT_RESOLVE_CONCURRENCY = 5

# Retry/backoff timing defaults.
STANDARD_RETRY_ATTEMPTS = 5
RETRY_BACKOFF_INITIAL_SEC = 1.0
RETRY_BACKOFF_EXP_BASE = 2.0
RETRY_BACKOFF_JITTER = 0.5
RETRY_BACKOFF_MAX_SEC = 60.0


def _normalize_timeout_value(value: Any, fallback: int | float) -> int | float:
    """Normalize timeout-like values to non-negative finite int/float."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        normalized = float(fallback)
    else:
        normalized = float(value)
    if not math.isfinite(normalized) or normalized < 0:
        normalized = float(fallback)
    if normalized.is_integer():
        return int(normalized)
    return normalized


def resolve_profile_timeout(profile: Mapping[str, Any] | None) -> int | float:
    """Resolve session/profile timeout with a safe default."""
    raw_timeout = None
    if isinstance(profile, Mapping):
        raw_timeout = profile.get("timeout")
    return _normalize_timeout_value(raw_timeout, DEFAULT_PROFILE_TIMEOUT_SEC)


def resolve_ai_read_timeout(
    profile_timeout_sec: int | float,
    *,
    search: bool = False,
) -> int | float:
    """Resolve AI-provider read timeout.

    When search is enabled, timeout is multiplied by
    ``AI_MODE_TIMEOUT_MULTIPLIER``.
    """
    timeout_sec = _normalize_timeout_value(
        profile_timeout_sec, DEFAULT_PROFILE_TIMEOUT_SEC
    )
    if timeout_sec <= 0:
        return timeout_sec
    if search:
        scaled = float(timeout_sec) * float(AI_MODE_TIMEOUT_MULTIPLIER)
        if scaled.is_integer():
            return int(scaled)
        return scaled
    return timeout_sec


def build_ai_httpx_timeout(read_timeout_sec: int | float) -> httpx.Timeout | None:
    """Build httpx timeout config for provider clients."""
    timeout_sec = _normalize_timeout_value(
        read_timeout_sec, DEFAULT_PROFILE_TIMEOUT_SEC
    )
    if timeout_sec <= 0:
        return None
    return httpx.Timeout(
        connect=AI_HTTP_CONNECT_TIMEOUT_SEC,
        read=timeout_sec,
        write=AI_HTTP_WRITE_TIMEOUT_SEC,
        pool=AI_HTTP_POOL_TIMEOUT_SEC,
    )
