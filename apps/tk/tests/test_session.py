"""Tests for session module."""

import pytest
from tk.session import Session


class TestSessionCreation:
    """Test Session dataclass creation and initialization."""

    def test_create_minimal_session(self):
        """Test creating session with minimal required fields."""
        session = Session()

        assert session.profile_path is None
        assert session.profile is None
        assert session.tasks is None
        assert session.last_list == []

    def test_session_defaults(self):
        """Test that session has correct default values."""
        session = Session()

        assert isinstance(session.last_list, list)
        assert len(session.last_list) == 0


class TestSessionRequireMethods:
    """Test require_profile and require_tasks methods."""

    def test_require_profile_with_profile(self, sample_session):
        """Test that require_profile returns profile when set."""
        profile = sample_session.require_profile()

        assert profile is not None
        assert "timezone" in profile

    def test_require_profile_without_profile(self, empty_session):
        """Test that require_profile raises ValueError when not set."""
        with pytest.raises(ValueError, match="No profile loaded"):
            empty_session.require_profile()

    def test_require_tasks_with_tasks(self, sample_session):
        """Test that require_tasks returns tasks when set."""
        tasks = sample_session.require_tasks()

        assert tasks is not None
        assert "tasks" in tasks

    def test_require_tasks_without_tasks(self, empty_session):
        """Test that require_tasks raises ValueError when not set."""
        with pytest.raises(ValueError, match="No tasks loaded"):
            empty_session.require_tasks()


class TestSessionListMapping:
    """Test list mapping functionality."""

    def test_set_last_list(self, empty_session):
        """Test setting list mapping."""
        mapping = [(1, 0), (2, 1), (3, 2)]
        empty_session.set_last_list(mapping)

        assert empty_session.last_list == mapping

    def test_clear_last_list(self, empty_session):
        """Test clearing list mapping."""
        empty_session.set_last_list([(1, 0), (2, 1)])
        empty_session.clear_last_list()

        assert empty_session.last_list == []

    def test_resolve_array_index(self, empty_session):
        """Test resolving display_num to array index."""
        empty_session.set_last_list([(1, 0), (2, 5), (3, 10)])

        assert empty_session.resolve_array_index(1) == 0
        assert empty_session.resolve_array_index(2) == 5
        assert empty_session.resolve_array_index(3) == 10

    def test_resolve_array_index_no_list(self, empty_session):
        """Test that resolving without list raises ValueError."""
        with pytest.raises(ValueError, match="Run 'list' or 'history' first"):
            empty_session.resolve_array_index(1)

    def test_resolve_array_index_invalid_num(self, empty_session):
        """Test that invalid display_num raises ValueError."""
        empty_session.set_last_list([(1, 0), (2, 1)])

        with pytest.raises(ValueError, match="Invalid task number"):
            empty_session.resolve_array_index(99)


class TestSessionTaskRetrieval:
    """Test task retrieval by display number."""

    def test_get_task_by_display_number(self, sample_session):
        """Test getting task by display number."""
        sample_session.set_last_list([(1, 0), (2, 1)])

        task = sample_session.get_task_by_display_number(1)

        assert task is not None
        assert task["text"] == "Task one"

    def test_get_task_by_display_number_invalid(self, sample_session):
        """Test that invalid display number raises ValueError."""
        sample_session.set_last_list([(1, 0)])

        with pytest.raises(ValueError, match="Invalid task number"):
            sample_session.get_task_by_display_number(99)

    def test_get_task_by_display_number_no_list(self, sample_session):
        """Test that getting task without list raises ValueError."""
        with pytest.raises(ValueError, match="Run 'list' or 'history' first"):
            sample_session.get_task_by_display_number(1)
