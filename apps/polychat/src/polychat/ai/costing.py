"""Cost estimation utilities."""

from __future__ import annotations

from dataclasses import dataclass

from .pricing import get_model_pricing
from .types import TokenUsage


@dataclass(frozen=True, slots=True)
class CostEstimate:
    """Breakdown of an estimated API call cost."""

    input_cost: float
    output_cost: float
    total_cost: float
    cached_input_tokens: int | None = None
    cache_write_tokens: int | None = None


def estimate_cost(
    model: str,
    usage: TokenUsage,
) -> CostEstimate | None:
    """Estimate USD cost for a single API call."""
    pricing = get_model_pricing(model)
    if pricing is None:
        return None

    prompt_tokens = usage.get("prompt_tokens", 0) or 0
    completion_tokens = usage.get("completion_tokens", 0) or 0
    cached_tokens = usage.get("cached_tokens")
    cache_write_tokens = usage.get("cache_write_tokens")

    if cached_tokens and pricing.cached_input_per_mtok is not None:
        non_cached = max(prompt_tokens - cached_tokens - (cache_write_tokens or 0), 0)
        input_cost = (
            non_cached * pricing.input_per_mtok
            + cached_tokens * pricing.cached_input_per_mtok
        ) / 1_000_000
        # Cache write surcharge (e.g. Claude charges 125% of input for writes).
        if cache_write_tokens and pricing.cache_write_per_mtok is not None:
            input_cost += cache_write_tokens * pricing.cache_write_per_mtok / 1_000_000
        elif cache_write_tokens:
            input_cost += cache_write_tokens * pricing.input_per_mtok / 1_000_000
    elif cache_write_tokens and pricing.cache_write_per_mtok is not None:
        non_cached = max(prompt_tokens - cache_write_tokens, 0)
        input_cost = (
            non_cached * pricing.input_per_mtok
            + cache_write_tokens * pricing.cache_write_per_mtok
        ) / 1_000_000
    else:
        input_cost = prompt_tokens * pricing.input_per_mtok / 1_000_000
        cached_tokens = None
        cache_write_tokens = None

    output_cost = completion_tokens * pricing.output_per_mtok / 1_000_000

    return CostEstimate(
        input_cost=input_cost,
        output_cost=output_cost,
        total_cost=input_cost + output_cost,
        cached_input_tokens=cached_tokens,
        cache_write_tokens=cache_write_tokens,
    )

