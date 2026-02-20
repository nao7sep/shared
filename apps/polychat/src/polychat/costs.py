"""Cost estimation for PolyChat.

Calculates estimated USD costs from token usage and model pricing data.
All costs are approximate — actual charges depend on provider billing.
"""

from dataclasses import dataclass

from .ai.types import TokenUsage
from .models import ModelPricing, get_model_pricing


@dataclass(frozen=True, slots=True)
class CostEstimate:
    """Breakdown of an estimated API call cost."""

    input_cost: float
    output_cost: float
    total_cost: float
    cached_input_tokens: int | None = None


def estimate_cost(
    model: str,
    usage: TokenUsage,
) -> CostEstimate | None:
    """Estimate USD cost for a single API call.

    Returns None when pricing data is unavailable for the model.
    """
    pricing = get_model_pricing(model)
    if pricing is None:
        return None

    prompt_tokens = usage.get("prompt_tokens", 0) or 0
    completion_tokens = usage.get("completion_tokens", 0) or 0
    cached_tokens = usage.get("cached_tokens")

    if cached_tokens and pricing.cached_input_per_mtok is not None:
        non_cached = max(prompt_tokens - cached_tokens, 0)
        input_cost = (
            non_cached * pricing.input_per_mtok
            + cached_tokens * pricing.cached_input_per_mtok
        ) / 1_000_000
    else:
        input_cost = prompt_tokens * pricing.input_per_mtok / 1_000_000
        cached_tokens = None

    output_cost = completion_tokens * pricing.output_per_mtok / 1_000_000

    return CostEstimate(
        input_cost=input_cost,
        output_cost=output_cost,
        total_cost=input_cost + output_cost,
        cached_input_tokens=cached_tokens,
    )


def format_cost_line(model: str, usage: TokenUsage) -> str | None:
    """Build a one-line cost summary for display after a response.

    Returns None when token usage or pricing data is missing.
    """
    prompt_tokens = usage.get("prompt_tokens")
    completion_tokens = usage.get("completion_tokens")
    if not prompt_tokens and not completion_tokens:
        return None

    est = estimate_cost(model, usage)

    parts: list[str] = []

    # Token counts
    token_parts: list[str] = []
    if prompt_tokens:
        token_parts.append(f"{prompt_tokens:,} in")
    if completion_tokens:
        token_parts.append(f"{completion_tokens:,} out")
    cached_tokens = usage.get("cached_tokens")
    if cached_tokens:
        token_parts.append(f"{cached_tokens:,} cached")
    parts.append(" / ".join(token_parts) + " tokens")

    # Cost
    if est is not None:
        if est.total_cost < 0.01:
            parts.append(f"~${est.total_cost:.4f}")
        else:
            parts.append(f"~${est.total_cost:.2f}")

    return " · ".join(parts) + " (estimated)"
