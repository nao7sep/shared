"""Tests for cost estimation module."""

import pytest
from polychat.ai.costing import estimate_cost
from polychat.formatting.costs import format_cost_line, format_cost_usd


# ---------------------------------------------------------------------------
# estimate_cost
# ---------------------------------------------------------------------------


def test_estimate_cost_unknown_model_returns_none():
    """Returns None when no pricing data exists for the model."""
    usage = {"prompt_tokens": 1000, "completion_tokens": 500}
    assert estimate_cost("unknown-model-xyz", usage) is None


def test_estimate_cost_plain_no_cache():
    """Correct cost when no cache fields are present."""
    # grok-2-vision-1212: input=$2.00/MTok, output=$10.00/MTok (no cache)
    usage = {"prompt_tokens": 1000, "completion_tokens": 500}
    est = estimate_cost("grok-2-vision-1212", usage)
    assert est is not None
    assert est.input_cost == pytest.approx(0.002)
    assert est.output_cost == pytest.approx(0.005)
    assert est.total_cost == pytest.approx(0.007)
    assert est.cached_input_tokens is None
    assert est.cache_write_tokens is None


def test_estimate_cost_zero_tokens():
    """All costs are zero when token counts are zero."""
    usage = {"prompt_tokens": 0, "completion_tokens": 0}
    est = estimate_cost("grok-2-vision-1212", usage)
    assert est is not None
    assert est.input_cost == pytest.approx(0.0)
    assert est.output_cost == pytest.approx(0.0)
    assert est.total_cost == pytest.approx(0.0)


def test_estimate_cost_with_cached_tokens():
    """Cached tokens are billed at the reduced rate; remainder at the full rate."""
    # claude-opus-4-6: input=$5.00/MTok, cached=$0.50/MTok, cache_write=$6.25/MTok
    # All prices are exact binary fractions.
    usage = {"prompt_tokens": 10000, "cached_tokens": 8000, "completion_tokens": 2000}
    est = estimate_cost("claude-opus-4-6", usage)
    assert est is not None
    # non-cached=2000; input=(2000*5.00 + 8000*0.50)/1M = 14000/1M
    assert est.input_cost == pytest.approx(0.014)
    assert est.output_cost == pytest.approx(0.05)
    assert est.total_cost == pytest.approx(0.064)
    assert est.cached_input_tokens == 8000
    assert est.cache_write_tokens is None


def test_estimate_cost_with_cached_and_cache_write():
    """Cached reads and cache writes are each billed at their respective rates."""
    # claude-opus-4-6: all prices are exact binary fractions.
    usage = {
        "prompt_tokens": 10000,
        "cached_tokens": 5000,
        "cache_write_tokens": 3000,
        "completion_tokens": 2000,
    }
    est = estimate_cost("claude-opus-4-6", usage)
    assert est is not None
    # non-cached=2000; input=(2000*5.00 + 5000*0.50)/1M + 3000*6.25/1M
    #   = 12500/1M + 18750/1M = 31250/1M
    assert est.input_cost == pytest.approx(0.03125)
    assert est.output_cost == pytest.approx(0.05)
    assert est.total_cost == pytest.approx(0.08125)
    assert est.cached_input_tokens == 5000
    assert est.cache_write_tokens == 3000


def test_estimate_cost_with_cache_write_only():
    """Cache writes without cached reads are billed at the cache-write rate."""
    # claude-opus-4-6
    usage = {
        "prompt_tokens": 10000,
        "cache_write_tokens": 3000,
        "completion_tokens": 2000,
    }
    est = estimate_cost("claude-opus-4-6", usage)
    assert est is not None
    # non-cached=7000; input=(7000*5.00 + 3000*6.25)/1M = 53750/1M
    assert est.input_cost == pytest.approx(0.05375)
    assert est.output_cost == pytest.approx(0.05)
    assert est.total_cost == pytest.approx(0.10375)
    assert est.cached_input_tokens is None
    assert est.cache_write_tokens == 3000


def test_estimate_cost_cache_write_falls_back_to_input_rate():
    """cache_write_tokens fall back to the regular input rate when the model
    has no cache_write_per_mtok in its pricing data."""
    # gpt-5-mini has cached_input_per_mtok but no cache_write_per_mtok.
    usage = {
        "prompt_tokens": 8000,
        "cached_tokens": 4000,
        "cache_write_tokens": 2000,
        "completion_tokens": 2000,
    }
    est = estimate_cost("gpt-5-mini", usage)
    assert est is not None
    # non-cached=2000; input=(2000*0.25 + 4000*0.025)/1M + 2000*0.25/1M (fallback rate)
    #   = (500+100)/1M + 500/1M = 1100/1M
    assert est.input_cost == pytest.approx(0.0011)
    assert est.output_cost == pytest.approx(0.004)
    assert est.total_cost == pytest.approx(0.0051)
    assert est.cached_input_tokens == 4000
    assert est.cache_write_tokens == 2000


# ---------------------------------------------------------------------------
# format_cost_usd
# ---------------------------------------------------------------------------


def test_format_cost_usd_zero():
    """Zero cost shows two decimal places."""
    assert format_cost_usd(0.0) == "$0.00"


def test_format_cost_usd_integer_only():
    """Number with no non-zero decimal digits uses 2 dp."""
    assert format_cost_usd(1.0) == "$1.00"


def test_format_cost_usd_large_integer_two_dp():
    """Two or more non-zeros in integer part → always 2 dp."""
    assert format_cost_usd(12.5) == "$12.50"


def test_format_cost_usd_second_nz_at_decimal_pos_1():
    """Second non-zero at decimal pos 1 (< 3) → 2 dp."""
    # nz_in_int=1 ("1"), second nz is "2" at decimal pos 1.
    assert format_cost_usd(100.2) == "$100.20"


def test_format_cost_usd_second_nz_at_decimal_pos_3_with_int_nz():
    """Second non-zero at decimal pos 3 → 3 dp (integer contributes one nz)."""
    # nz_in_int=1 ("1"), second nz is "2" at decimal pos 3.
    assert format_cost_usd(100.0023) == "$100.002"


def test_format_cost_usd_two_nz_in_decimal_both_beyond_pos_2():
    """Both non-zeros in decimal; second at pos 3 → 3 dp."""
    # nz_in_int=0, nz_needed=2: "1" at pos 2, "2" at pos 3.
    assert format_cost_usd(0.0123) == "$0.012"


def test_format_cost_usd_two_nz_deep_in_decimal():
    """Second non-zero deep in decimal → use that position as precision."""
    # nz_in_int=0, nz_needed=2: "1" at pos 4, "2" at pos 5.
    assert format_cost_usd(0.000123) == "$0.00012"


def test_format_cost_usd_single_decimal_nz_at_pos_3():
    """Only one non-zero digit at decimal pos 3 → fallback max(2, 3) = 3 dp."""
    assert format_cost_usd(0.007) == "$0.007"


def test_format_cost_usd_single_decimal_nz_at_pos_2():
    """Only one non-zero digit at decimal pos 2 → fallback max(2, 2) = 2 dp."""
    assert format_cost_usd(0.06) == "$0.06"


def test_format_cost_usd_distinguishes_similar_costs():
    """Values that differ only at the 3rd decimal place are shown distinctly."""
    # 0.010 has only one non-zero decimal digit ("1" at pos 2) → 2 dp.
    assert format_cost_usd(0.010) == "$0.01"
    # 0.019 has a second non-zero ("9") at decimal pos 3 → 3 dp.
    assert format_cost_usd(0.019) == "$0.019"


# ---------------------------------------------------------------------------
# format_cost_line
# ---------------------------------------------------------------------------


def test_format_cost_line_empty_usage_returns_none():
    """Returns None when the usage dict has no token counts."""
    assert format_cost_line("grok-2-vision-1212", {}) is None


def test_format_cost_line_zero_tokens_returns_none():
    """Returns None when both token counts are zero."""
    usage = {"prompt_tokens": 0, "completion_tokens": 0}
    assert format_cost_line("grok-2-vision-1212", usage) is None


def test_format_cost_line_no_pricing_data():
    """Shows token counts and model name even when pricing is unavailable."""
    usage = {"prompt_tokens": 1000, "completion_tokens": 500}
    result = format_cost_line("unknown-model-xyz", usage)
    assert result == "1,000 input, 500 output | unknown-model-xyz"


def test_format_cost_line_small_cost_three_decimals():
    """Costs with a single non-zero decimal digit at position 3 use 3 dp."""
    # grok-2-vision-1212: total = 1000*2.00/1M + 500*10.00/1M = 0.007
    # "7" is the only non-zero decimal digit (at pos 3) → precision = max(2, 3) = 3.
    usage = {"prompt_tokens": 1000, "completion_tokens": 500}
    result = format_cost_line("grok-2-vision-1212", usage)
    assert result == "$0.007 estimated | 1,000 input, 500 output | grok-2-vision-1212"


def test_format_cost_line_cost_two_decimals():
    """Costs whose second non-zero decimal digit is at pos <= 2 use 2 dp."""
    # claude-sonnet-4-6: total = 10000*3.00/1M + 2000*15.00/1M = 0.060
    # "6" at pos 2 is the only non-zero → precision = max(2, 2) = 2.
    usage = {"prompt_tokens": 10000, "completion_tokens": 2000}
    result = format_cost_line("claude-sonnet-4-6", usage)
    assert result == "$0.06 estimated | 10,000 input, 2,000 output | claude-sonnet-4-6"


def test_format_cost_line_cached_tokens_only():
    """Cached token count appears in parentheses after the total input count."""
    # claude-opus-4-6: total = (2000*5.00 + 2000*0.50)/1M + 1000*25.00/1M
    #   = 11000/1M + 25000/1M = 0.036
    # "3" at pos 2, "6" at pos 3 → second_nz_decimal_pos=3 → 3 dp.
    usage = {"prompt_tokens": 4000, "cached_tokens": 2000, "completion_tokens": 1000}
    result = format_cost_line("claude-opus-4-6", usage)
    assert result == "$0.036 estimated | 4,000 input (2,000 cached), 1,000 output | claude-opus-4-6"


def test_format_cost_line_cache_write_tokens_only():
    """Cache-write token count appears in parentheses when there are no cached reads."""
    # claude-opus-4-6: total = (7000*5.00 + 3000*6.25)/1M + 2000*25.00/1M
    #   = 53750/1M + 50000/1M = 0.10375
    # "1" at pos 1, "3" at pos 3 → second_nz_decimal_pos=3 → 3 dp → rounds to 0.104.
    usage = {"prompt_tokens": 10000, "cache_write_tokens": 3000, "completion_tokens": 2000}
    result = format_cost_line("claude-opus-4-6", usage)
    assert result == "$0.104 estimated | 10,000 input (3,000 cache-write), 2,000 output | claude-opus-4-6"


def test_format_cost_line_input_is_true_total_not_remainder():
    """The input count shown is the true total (regular + cached + cache-write),
    not the non-cached remainder.  Anthropic returns input_tokens as only the
    regular portion; the provider must sum all three fields before populating
    prompt_tokens so that display and cost math both see the correct total."""
    # Mirrors the real-world case: 3 regular + 8958 cache-write = 8961 total.
    # claude-haiku-4-5: input=$1.00/MTok, cache_write=$1.25/MTok, output=$5.00/MTok
    usage = {"prompt_tokens": 8961, "cache_write_tokens": 8958, "completion_tokens": 57}
    result = format_cost_line("claude-haiku-4-5", usage)
    # Input display must be 8,961 (the total), not 3 (the remainder).
    assert result is not None
    assert result.startswith("$")
    assert "8,961 input (8,958 cache-write)" in result
    assert "57 output" in result
    assert result.endswith("claude-haiku-4-5")


def test_format_cost_line_cached_and_cache_write():
    """Both cached reads and cache writes appear together in parentheses."""
    # claude-opus-4-6: total = 31250/1M + 50000/1M = 0.08125
    # "8" at pos 2, "1" at pos 3 → second_nz_decimal_pos=3 → 3 dp → rounds to 0.081.
    usage = {
        "prompt_tokens": 10000,
        "cached_tokens": 5000,
        "cache_write_tokens": 3000,
        "completion_tokens": 2000,
    }
    result = format_cost_line("claude-opus-4-6", usage)
    assert result == (
        "$0.081 estimated | 10,000 input (5,000 cached, 3,000 cache-write), "
        "2,000 output | claude-opus-4-6"
    )


def test_format_cost_line_thousands_separator():
    """Token counts above 999 use comma separators."""
    # grok-2-vision-1212: total = 10000*2.00/1M + 5000*10.00/1M = 0.07
    usage = {"prompt_tokens": 10000, "completion_tokens": 5000}
    result = format_cost_line("grok-2-vision-1212", usage)
    assert result == "$0.07 estimated | 10,000 input, 5,000 output | grok-2-vision-1212"


def test_format_cost_line_output_only():
    """Responses with no input tokens show only the output count."""
    # grok-2-vision-1212: total = 500*10.00/1M = 0.005
    # "5" at pos 3 is the only non-zero → precision = max(2, 3) = 3.
    usage = {"completion_tokens": 500}
    result = format_cost_line("grok-2-vision-1212", usage)
    assert result == "$0.005 estimated | 500 output | grok-2-vision-1212"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
