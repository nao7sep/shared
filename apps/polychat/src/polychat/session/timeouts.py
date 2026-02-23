"""Timeout normalization and formatting helpers for session state."""

from __future__ import annotations

import math
from typing import Any


def normalize_timeout(value: Any) -> int | float:
    """Normalize timeout to int/float and reject invalid values."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Timeout must be a non-negative finite number")
    numeric = float(value)
    if not math.isfinite(numeric) or numeric < 0:
        raise ValueError("Timeout must be a non-negative finite number")
    if numeric.is_integer():
        return int(numeric)
    return numeric


def format_timeout(timeout: int | float) -> str:
    """Format timeout value for user-facing messages."""
    if timeout == 0:
        return "0 (wait forever)"
    return f"{timeout} seconds"
