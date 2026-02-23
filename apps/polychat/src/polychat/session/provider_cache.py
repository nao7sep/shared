"""Provider-cache helpers for session state."""

from __future__ import annotations

from typing import Any, Optional

from .state import SessionState


def get_cached_provider(
    state: SessionState,
    provider_name: str,
    api_key: str,
    timeout_sec: int | float | None = None,
) -> Optional[Any]:
    """Get cached provider instance."""
    return state.get_cached_provider(provider_name, api_key, timeout_sec=timeout_sec)


def cache_provider(
    state: SessionState,
    provider_name: str,
    api_key: str,
    instance: Any,
    timeout_sec: int | float | None = None,
) -> None:
    """Cache provider instance."""
    state.cache_provider(provider_name, api_key, instance, timeout_sec=timeout_sec)


def clear_provider_cache(state: SessionState) -> None:
    """Clear all cached provider instances."""
    state.clear_provider_cache()

