"""Compatibility shim for legacy ``polychat.helper_ai`` imports."""

from __future__ import annotations

import sys

from .ai import helper_runtime as _helper_runtime

sys.modules[__name__] = _helper_runtime
