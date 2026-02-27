"""Tests for markdown module."""

import pytest
from pathlib import Path

from tk.markdown import generate_todo


class TestGenerateTodo:
    """Test generate_todo function."""

    def test_generate_todo_empty(self, temp_dir):
        """Test generating TODO.md with no tasks."""
        output_path = temp_dir / "TODO.md"

        generate_todo([], str(output_path))

        content = output_path.read_text()
        assert "# TODO" in content
        assert "No pending tasks." in content

    def test_generate_todo_pending_only(self, temp_dir):
        """Test generating TODO.md with only pending tasks."""
        output_path = temp_dir / "TODO.md"
        tasks = [
            {
                "text": "Task one",
                "status": "pending",
                "created_utc": "2026-02-01T10:00:00+00:00",
                "handled_utc": None,
                "subjective_date": None,
                "note": None,
            },
            {
                "text": "Task two",
                "status": "pending",
                "created_utc": "2026-02-02T10:00:00+00:00",
                "handled_utc": None,
                "subjective_date": None,
                "note": None,
            },
        ]

        generate_todo(tasks, str(output_path))

        content = output_path.read_text()
        assert "- Task one" in content
        assert "- Task two" in content
        assert "## History" not in content

    def test_generate_todo_with_history(self, temp_dir, sample_tasks_data):
        """Test generating TODO.md with history section."""
        output_path = temp_dir / "TODO.md"

        generate_todo(sample_tasks_data["tasks"], str(output_path))

        content = output_path.read_text()
        assert "# TODO" in content
        assert "## History" in content
        assert "### 2026-02-03" in content
        assert "### 2026-02-02" in content

    def test_generate_todo_creates_directory(self, temp_dir):
        """Test that generate_todo creates parent directory."""
        output_path = temp_dir / "subdir" / "TODO.md"

        generate_todo([], str(output_path))

        assert output_path.exists()
        assert output_path.parent.exists()

    def test_generate_todo_format(self, temp_dir):
        """Test correct markdown format."""
        output_path = temp_dir / "TODO.md"

        generate_todo([], str(output_path))

        content = output_path.read_text()
        lines = content.split("\n")

        assert lines[0] == "# TODO"
        assert lines[1] == ""  # Empty line after header
        assert lines[-1] == ""  # File ends with empty line

    def test_generate_todo_dates_descending(self, temp_dir):
        """Test that history dates are descending."""
        output_path = temp_dir / "TODO.md"
        tasks = [
            {
                "text": "Task 1",
                "status": "done",
                "created_utc": "2026-02-07T10:00:00+00:00",
                "handled_utc": "2026-02-07T15:00:00+00:00",
                "subjective_date": "2026-02-07",
                "note": None,
            },
            {
                "text": "Task 2",
                "status": "done",
                "created_utc": "2026-02-09T10:00:00+00:00",
                "handled_utc": "2026-02-09T15:00:00+00:00",
                "subjective_date": "2026-02-09",
                "note": None,
            },
            {
                "text": "Task 3",
                "status": "done",
                "created_utc": "2026-02-08T10:00:00+00:00",
                "handled_utc": "2026-02-08T15:00:00+00:00",
                "subjective_date": "2026-02-08",
                "note": None,
            },
        ]

        generate_todo(tasks, str(output_path))

        content = output_path.read_text()
        # 2026-02-09 should appear before 2026-02-08
        pos_09 = content.find("2026-02-09")
        pos_08 = content.find("2026-02-08")
        pos_07 = content.find("2026-02-07")

        assert pos_09 < pos_08 < pos_07

    def test_generate_todo_tasks_within_date(self, temp_dir):
        """Test that tasks within date are sorted by handled_utc."""
        output_path = temp_dir / "TODO.md"
        tasks = [
            {
                "text": "Task at 12:00",
                "status": "done",
                "created_utc": "2026-02-09T10:00:00+00:00",
                "handled_utc": "2026-02-09T12:00:00+00:00",
                "subjective_date": "2026-02-09",
                "note": None,
            },
            {
                "text": "Task at 10:00",
                "status": "done",
                "created_utc": "2026-02-09T08:00:00+00:00",
                "handled_utc": "2026-02-09T10:00:00+00:00",
                "subjective_date": "2026-02-09",
                "note": None,
            },
        ]

        generate_todo(tasks, str(output_path))

        content = output_path.read_text()
        # "Task at 10:00" should appear before "Task at 12:00"
        pos_10 = content.find("Task at 10:00")
        pos_12 = content.find("Task at 12:00")

        assert pos_10 < pos_12

    def test_generate_todo_with_notes(self, temp_dir):
        """Test that notes are included with => format."""
        output_path = temp_dir / "TODO.md"
        tasks = [
            {
                "text": "Task with note",
                "status": "done",
                "created_utc": "2026-02-09T10:00:00+00:00",
                "handled_utc": "2026-02-09T15:00:00+00:00",
                "subjective_date": "2026-02-09",
                "note": "This is a note",
            },
        ]

        generate_todo(tasks, str(output_path))

        content = output_path.read_text()
        assert "Task with note => This is a note" in content

    def test_generate_todo_status_emoji(self, temp_dir):
        """Test that status emojis are correct."""
        output_path = temp_dir / "TODO.md"
        tasks = [
            {
                "text": "Done task",
                "status": "done",
                "created_utc": "2026-02-09T10:00:00+00:00",
                "handled_utc": "2026-02-09T15:00:00+00:00",
                "subjective_date": "2026-02-09",
                "note": None,
            },
            {
                "text": "Cancelled task",
                "status": "cancelled",
                "created_utc": "2026-02-09T10:00:00+00:00",
                "handled_utc": "2026-02-09T16:00:00+00:00",
                "subjective_date": "2026-02-09",
                "note": None,
            },
        ]

        generate_todo(tasks, str(output_path))

        content = output_path.read_text()
        assert "✅ Done task" in content
        assert "❌ Cancelled task" in content

    def test_generate_todo_mixed_statuses(self, temp_dir):
        """Test that done and cancelled tasks are merged by date."""
        output_path = temp_dir / "TODO.md"
        tasks = [
            {
                "text": "Done task",
                "status": "done",
                "created_utc": "2026-02-09T10:00:00+00:00",
                "handled_utc": "2026-02-09T15:00:00+00:00",
                "subjective_date": "2026-02-09",
                "note": None,
            },
            {
                "text": "Cancelled task",
                "status": "cancelled",
                "created_utc": "2026-02-09T11:00:00+00:00",
                "handled_utc": "2026-02-09T16:00:00+00:00",
                "subjective_date": "2026-02-09",
                "note": None,
            },
        ]

        generate_todo(tasks, str(output_path))

        content = output_path.read_text()
        # Both should be under the same date heading
        assert content.count("### 2026-02-09") == 1
        assert "✅ Done task" in content
        assert "❌ Cancelled task" in content
