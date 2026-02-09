"""Pytest configuration and fixtures for tk tests."""

import json
import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timezone

from tk.session import Session


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_profile(temp_dir):
    """Create sample profile JSON for testing."""
    profile = {
        "timezone": "Asia/Tokyo",
        "subjective_day_start": "04:00:00",
        "data_path": str(temp_dir / "tasks.json"),
        "output_path": str(temp_dir / "TODO.md"),
        "auto_sync": True,
        "sync_on_exit": False,
    }

    profile_path = temp_dir / "test-profile.json"
    with open(profile_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2)

    return profile_path


@pytest.fixture
def sample_tasks_data():
    """Create sample tasks data structure."""
    return {
        "tasks": [
            {
                "text": "Task one",
                "status": "pending",
                "created_at": "2026-02-01T10:00:00+00:00",
                "handled_at": None,
                "subjective_date": None,
                "note": None,
            },
            {
                "text": "Task two",
                "status": "done",
                "created_at": "2026-02-02T10:00:00+00:00",
                "handled_at": "2026-02-02T15:00:00+00:00",
                "subjective_date": "2026-02-02",
                "note": "Completed successfully",
            },
            {
                "text": "Task three",
                "status": "cancelled",
                "created_at": "2026-02-03T10:00:00+00:00",
                "handled_at": "2026-02-03T12:00:00+00:00",
                "subjective_date": "2026-02-03",
                "note": None,
            },
        ]
    }


@pytest.fixture
def sample_session(temp_dir, sample_tasks_data):
    """Create initialized Session object."""
    profile = {
        "timezone": "Asia/Tokyo",
        "subjective_day_start": "04:00:00",
        "data_path": str(temp_dir / "tasks.json"),
        "output_path": str(temp_dir / "TODO.md"),
        "auto_sync": False,  # Disable for most tests
        "sync_on_exit": False,
    }

    session = Session()
    session.profile_path = str(temp_dir / "profile.json")
    session.profile = profile
    session.tasks = sample_tasks_data

    return session


@pytest.fixture
def empty_session():
    """Create empty Session for testing error cases."""
    return Session()


@pytest.fixture
def frozen_time():
    """Freeze time for consistent time-dependent tests."""
    from freezegun import freeze_time
    with freeze_time("2026-02-09 10:00:00"):
        yield
