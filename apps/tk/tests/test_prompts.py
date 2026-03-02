"""Tests for prompts module."""

import pytest
from tk import prompts
from tk.models import Task, TaskStatus


class TestCollectDonePrompts:
    """Test collect_done_cancel_prompts function."""

    def test_collect_done_prompts_with_note(self, monkeypatch):
        """Test collecting prompts with note input."""
        task = Task(text="Test task", status="pending", created_utc="2026-02-09T10:00:00+00:00")
        inputs = iter(["My note", ""])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))

        result = prompts.collect_done_cancel_prompts(
            task, TaskStatus.DONE, "2026-02-09"
        )

        assert result.note == "My note"
        assert result.date == "2026-02-09"

    def test_collect_done_prompts_skip_note(self, monkeypatch):
        """Test collecting prompts with empty note."""
        task = Task(text="Test task", status="pending", created_utc="2026-02-09T10:00:00+00:00")
        inputs = iter(["", ""])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))

        result = prompts.collect_done_cancel_prompts(
            task, TaskStatus.DONE, "2026-02-09"
        )

        assert result.note is None
        assert result.date == "2026-02-09"

    def test_collect_done_prompts_with_date(self, monkeypatch):
        """Test collecting prompts with custom date."""
        task = Task(text="Test task", status="pending", created_utc="2026-02-09T10:00:00+00:00")
        inputs = iter(["Note", "2026-02-05"])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))

        result = prompts.collect_done_cancel_prompts(
            task, TaskStatus.DONE, "2026-02-09"
        )

        assert result.note == "Note"
        assert result.date == "2026-02-05"

    def test_collect_done_prompts_default_date(self, monkeypatch):
        """Test collecting prompts using default date."""
        task = Task(text="Test task", status="pending", created_utc="2026-02-09T10:00:00+00:00")
        inputs = iter(["Note", ""])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))

        result = prompts.collect_done_cancel_prompts(
            task, TaskStatus.DONE, "2026-02-09"
        )

        assert result.date == "2026-02-09"

    def test_collect_done_prompts_cancelled(self, monkeypatch):
        """Test handling Ctrl+C cancellation."""
        task = Task(text="Test task", status="pending", created_utc="2026-02-09T10:00:00+00:00")

        def mock_input(_):
            raise KeyboardInterrupt()

        monkeypatch.setattr("builtins.input", mock_input)

        result = prompts.collect_done_cancel_prompts(
            task, TaskStatus.DONE, "2026-02-09"
        )

        assert result == "CANCELLED"

    def test_collect_done_prompts_invalid_date(self, monkeypatch):
        """Test that invalid date raises ValueError."""
        task = Task(text="Test task", status="pending", created_utc="2026-02-09T10:00:00+00:00")
        inputs = iter(["Note", "invalid-date"])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))

        with pytest.raises(ValueError, match="Invalid date"):
            prompts.collect_done_cancel_prompts(
                task, TaskStatus.DONE, "2026-02-09"
            )


class TestCollectDeleteConfirmation:
    """Test collect_delete_confirmation function."""

    def test_collect_delete_confirmation_yes(self, monkeypatch):
        """Test confirmation with 'yes'."""
        task = Task(text="Test task", status="pending", created_utc="2026-02-09T10:00:00+00:00")
        monkeypatch.setattr("builtins.input", lambda _: "yes")

        result = prompts.collect_delete_confirmation(task)

        assert result is True

    def test_collect_delete_confirmation_no(self, monkeypatch):
        """Test confirmation with 'no'."""
        task = Task(text="Test task", status="pending", created_utc="2026-02-09T10:00:00+00:00")
        monkeypatch.setattr("builtins.input", lambda _: "no")

        result = prompts.collect_delete_confirmation(task)

        assert result is False

    def test_collect_delete_confirmation_empty(self, monkeypatch):
        """Test confirmation with empty input."""
        task = Task(text="Test task", status="pending", created_utc="2026-02-09T10:00:00+00:00")
        monkeypatch.setattr("builtins.input", lambda _: "")

        result = prompts.collect_delete_confirmation(task)

        assert result is False

    def test_collect_delete_confirmation_case_insensitive(self, monkeypatch):
        """Test that confirmation is case insensitive."""
        task = Task(text="Test task", status="pending", created_utc="2026-02-09T10:00:00+00:00")
        monkeypatch.setattr("builtins.input", lambda _: "YES")

        result = prompts.collect_delete_confirmation(task)

        assert result is True
