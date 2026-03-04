from __future__ import annotations

from viber.output_segments import reset_output_segments


def pytest_runtest_setup() -> None:
    reset_output_segments()
