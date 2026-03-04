from __future__ import annotations

import sys
from pathlib import Path

import pytest

from revzip.output_segments import reset_output_segments

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


@pytest.fixture(autouse=True)
def _reset_output_segments() -> None:
    reset_output_segments()
