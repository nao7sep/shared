"""Cost estimation for PolyChat.

Calculates estimated USD costs from token usage and model pricing data.
All costs are approximate and actual charges depend on provider billing.
"""

from dataclasses import dataclass

from .ai.types import TokenUsage
from .models import get_model_pricing


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
    """Estimate USD cost for a single API call.

    Returns None when pricing data is unavailable for the model.
    """
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
        # Cache write surcharge (e.g. Claude charges 125% of input for writes)
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


def format_cost_usd(value: float) -> str:
    """Format a USD cost with adaptive decimal precision.

    Always shows at least 2 decimal places.  Locates the 2nd non-zero
    digit across the full number (integer part first, then decimal).
    If that digit falls at decimal position >= 3, that position is used
    as the display precision.  Otherwise precision is max(2, position of
    the first non-zero decimal digit).

    Examples:
        1.0      -> "$1.00"
        100.2    -> "$100.20"
        100.0023 -> "$100.002"
        0.0123   -> "$0.012"
        0.000123 -> "$0.00012"
        0.007    -> "$0.007"
        0.06     -> "$0.06"
    """
    MAX_SCAN = 10
    s = f"{abs(value):.{MAX_SCAN}f}"
    dot_idx = s.index(".")
    integer_str = s[:dot_idx]
    decimal_str = s[dot_idx + 1:]

    nz_in_int = sum(1 for c in integer_str if c != "0")
    if nz_in_int >= 2:
        # Integer part alone supplies 2+ significant figures → 2 dp is enough.
        return f"${value:.2f}"

    # How many more non-zero digits we need from the decimal part.
    nz_needed = 2 - nz_in_int  # 1 or 2

    first_decimal_nz_pos = 0
    second_nz_decimal_pos = 0
    nz_count = 0

    for i, c in enumerate(decimal_str, start=1):
        if c != "0":
            nz_count += 1
            if nz_count == 1:
                first_decimal_nz_pos = i
            if nz_count == nz_needed:
                second_nz_decimal_pos = i
                break

    if second_nz_decimal_pos >= 3:
        precision = second_nz_decimal_pos
    elif first_decimal_nz_pos > 0:
        precision = max(2, first_decimal_nz_pos)
    else:
        precision = 2

    return f"${value:.{precision}f}"


def format_cost_line(model: str, usage: TokenUsage) -> str | None:
    """Build a one-line cost summary for display after a response.

    Format: cost | N input (N cached, N cache-write), N output | model

    The parenthetical breakdown is omitted when neither cached nor
    cache-write token counts are available.  If only one is present,
    only that value appears inside the parentheses.

    Returns None when token usage or pricing data is missing.
    """
    prompt_tokens = usage.get("prompt_tokens", 0) or 0
    completion_tokens = usage.get("completion_tokens", 0) or 0
    if not prompt_tokens and not completion_tokens:
        return None

    est = estimate_cost(model, usage)

    parts: list[str] = []

    # Cost (leading element so the user sees price first)
    if est is not None:
        parts.append(f"{format_cost_usd(est.total_cost)} estimated")

    # Token counts: "N input (N cached, N cache-write), N output"
    cached_tokens = usage.get("cached_tokens")
    cache_write_tokens = usage.get("cache_write_tokens")

    token_parts: list[str] = []

    if prompt_tokens:
        paren_parts: list[str] = []
        if cached_tokens:
            paren_parts.append(f"{cached_tokens:,} cached")
        if cache_write_tokens:
            paren_parts.append(f"{cache_write_tokens:,} cache-write")
        if paren_parts:
            token_parts.append(f"{prompt_tokens:,} input ({', '.join(paren_parts)})")
        else:
            token_parts.append(f"{prompt_tokens:,} input")

    if completion_tokens:
        token_parts.append(f"{completion_tokens:,} output")

    if token_parts:
        parts.append(", ".join(token_parts))

    # Model name so the user can verify which model was used
    parts.append(model)

    return " | ".join(parts)
