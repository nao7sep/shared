"""Compatibility shim for legacy ``polychat.ai_runtime`` imports."""

from __future__ import annotations

import sys

from .ai import runtime as _runtime

sys.modules[__name__] = _runtime
