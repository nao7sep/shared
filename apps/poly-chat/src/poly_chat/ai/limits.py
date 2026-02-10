"""Centralized optional AI response/thinking limits.

Resolved precedence order:
1. ``ai_limits.default``
2. ``ai_limits.providers.<provider>``
3. ``ai_limits.helper`` (helper invocations only)

All fields are optional; ``None`` means "omit this parameter from provider calls".
"""

from __future__ import annotations

from typing import Any, Mapping, TypedDict


class AIRequestLimits(TypedDict, total=False):
    """Resolved per-request limits consumed by providers.

    All keys are optional. ``None`` means "do not set this provider parameter".
    """

    max_output_tokens: int | None
    search_max_output_tokens: int | None
    thinking_budget_tokens: int | None


def _normalize_optional_limit(raw_value: Any) -> int | None:
    """Normalize a configured limit value to positive int or None."""
    if raw_value is None:
        return None
    if isinstance(raw_value, bool):
        return None
    if isinstance(raw_value, int) and raw_value > 0:
        return raw_value
    return None


def _read_limit_block(config: Mapping[str, Any] | None) -> AIRequestLimits:
    if not isinstance(config, Mapping):
        return {}

    limits: AIRequestLimits = {}
    for key in (
        "max_output_tokens",
        "search_max_output_tokens",
        "thinking_budget_tokens",
    ):
        if key in config:
            limits[key] = _normalize_optional_limit(config.get(key))
    return limits


def resolve_profile_limits(
    profile: Mapping[str, Any] | None,
    provider: str,
    *,
    helper: bool = False,
) -> AIRequestLimits:
    """Resolve effective limits from profile-level configuration.

    Expected optional profile structure:

    {
      "ai_limits": {
        "default": {...},
        "providers": {"claude": {...}},
        "helper": {...}
      }
    }
    """
    if not isinstance(profile, Mapping):
        return {}

    raw_limits = profile.get("ai_limits")
    if not isinstance(raw_limits, Mapping):
        return {}

    resolved: AIRequestLimits = {}
    resolved.update(_read_limit_block(raw_limits.get("default")))

    providers = raw_limits.get("providers")
    if isinstance(providers, Mapping):
        resolved.update(_read_limit_block(providers.get(provider)))

    if helper:
        resolved.update(_read_limit_block(raw_limits.get("helper")))

    return resolved


def select_max_output_tokens(limits: Mapping[str, Any], *, search: bool) -> int | None:
    """Select max output tokens for this request mode."""
    if search:
        search_limit = _normalize_optional_limit(limits.get("search_max_output_tokens"))
        if search_limit is not None:
            return search_limit
    return _normalize_optional_limit(limits.get("max_output_tokens"))
