"""Cost display formatters."""

from __future__ import annotations

from ..ai.costing import estimate_cost
from ..ai.types import TokenUsage


def format_cost_usd(value: float) -> str:
    """Format a USD cost with adaptive decimal precision."""
    max_scan = 10
    scanned = f"{abs(value):.{max_scan}f}"
    dot_idx = scanned.index(".")
    integer_str = scanned[:dot_idx]
    decimal_str = scanned[dot_idx + 1 :]

    nz_in_int = sum(1 for c in integer_str if c != "0")
    if nz_in_int >= 2:
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
    """Build a one-line cost summary for display after a response."""
    prompt_tokens = usage.get("prompt_tokens", 0) or 0
    completion_tokens = usage.get("completion_tokens", 0) or 0
    if not prompt_tokens and not completion_tokens:
        return None

    est = estimate_cost(model, usage)

    parts: list[str] = []

    # Cost (leading element so the user sees price first).
    if est is not None:
        parts.append(f"{format_cost_usd(est.total_cost)} estimated")

    # Token counts: "N input (N cached, N cache-write), N output".
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

    # Model name so the user can verify which model was used.
    parts.append(model)

    return " | ".join(parts)

