"""Tests for data module."""

import json
import pytest
from pathlib import Path
from datetime import datetime, timezone

from tk import data


class TestLoadTasks:
    """Test load_tasks function."""

    def test_load_tasks_nonexistent_file(self, temp_dir):
        """Test loading tasks from non-existent file returns empty structure."""
        path = temp_dir / "nonexistent.json"
        result = data.load_tasks(str(path))

        assert result == {"tasks": []}
        assert not path.exists()

    def test_load_tasks_creates_directory(self, temp_dir):
        """Test that load_tasks creates parent directory."""
        path = temp_dir / "subdir" / "tasks.json"
        result = data.load_tasks(str(path))

        assert result == {"tasks": []}
        assert path.parent.exists()

    def test_load_tasks_valid_file(self, temp_dir, sample_tasks_data):
        """Test loading valid tasks file."""
        path = temp_dir / "tasks.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(sample_tasks_data, f)

        result = data.load_tasks(str(path))

        assert result == sample_tasks_data
        assert len(result["tasks"]) == 3

    def test_load_tasks_invalid_json(self, temp_dir):
        """Test that invalid JSON raises ValueError."""
        path = temp_dir / "invalid.json"
        path.write_text("{ invalid json }")

        with pytest.raises(ValueError, match="Invalid JSON"):
            data.load_tasks(str(path))

    def test_load_tasks_missing_tasks_key(self, temp_dir):
        """Test that missing 'tasks' key raises ValueError."""
        path = temp_dir / "notasks.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"other": []}, f)

        with pytest.raises(ValueError, match="missing 'tasks' key"):
            data.load_tasks(str(path))


class TestValidateTasksStructure:
    """Test validate_tasks_structure function."""

    def test_validate_empty_tasks(self):
        """Test that empty tasks array is valid."""
        data.validate_tasks_structure({"tasks": []})  # Should not raise

    def test_validate_valid_tasks(self):
        """Test that well-formed tasks are valid."""
        valid_data = {
            "tasks": [
                {
                    "text": "Test task",
                    "status": "pending",
                    "created_at": "2026-02-09T10:00:00+00:00",
                    "handled_at": None,
                    "subjective_date": None,
                    "note": None,
                }
            ]
        }
        data.validate_tasks_structure(valid_data)  # Should not raise

    def test_validate_missing_tasks_key(self):
        """Test that missing 'tasks' key raises ValueError."""
        with pytest.raises(ValueError, match="missing 'tasks' key"):
            data.validate_tasks_structure({"other": []})

    def test_validate_tasks_not_array(self):
        """Test that 'tasks' must be an array."""
        with pytest.raises(ValueError, match="'tasks' must be an array"):
            data.validate_tasks_structure({"tasks": "not an array"})

        with pytest.raises(ValueError, match="'tasks' must be an array"):
            data.validate_tasks_structure({"tasks": {}})

    def test_validate_missing_required_fields(self):
        """Test that missing required fields raises ValueError."""
        # Missing 'text'
        with pytest.raises(ValueError, match="missing required fields"):
            data.validate_tasks_structure({
                "tasks": [{"status": "pending", "created_at": "2026-02-09T10:00:00+00:00"}]
            })

        # Missing 'status'
        with pytest.raises(ValueError, match="missing required fields"):
            data.validate_tasks_structure({
                "tasks": [{"text": "Test", "created_at": "2026-02-09T10:00:00+00:00"}]
            })

        # Missing 'created_at'
        with pytest.raises(ValueError, match="missing required fields"):
            data.validate_tasks_structure({
                "tasks": [{"text": "Test", "status": "pending"}]
            })

    def test_validate_invalid_status(self):
        """Test that invalid status raises ValueError."""
        with pytest.raises(ValueError, match="invalid status"):
            data.validate_tasks_structure({
                "tasks": [{
                    "text": "Test",
                    "status": "invalid_status",
                    "created_at": "2026-02-09T10:00:00+00:00",
                }]
            })

    def test_validate_task_not_dict(self):
        """Test that non-dict tasks raise ValueError."""
        with pytest.raises(ValueError, match="not a valid object"):
            data.validate_tasks_structure({"tasks": ["not a dict"]})

        with pytest.raises(ValueError, match="not a valid object"):
            data.validate_tasks_structure({"tasks": [123]})


class TestSaveTasks:
    """Test save_tasks function."""

    def test_save_tasks_creates_directory(self, temp_dir):
        """Test that save_tasks creates parent directory."""
        path = temp_dir / "subdir" / "tasks.json"
        tasks_data = {"tasks": []}

        data.save_tasks(str(path), tasks_data)

        assert path.exists()
        assert path.parent.exists()

    def test_save_tasks_writes_valid_json(self, temp_dir, sample_tasks_data):
        """Test that save_tasks writes valid JSON."""
        path = temp_dir / "tasks.json"

        data.save_tasks(str(path), sample_tasks_data)

        # Read it back
        with open(path, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        assert loaded == sample_tasks_data

    def test_save_tasks_preserves_encoding(self, temp_dir):
        """Test that UTF-8 encoding works correctly."""
        path = temp_dir / "tasks.json"
        tasks_data = {
            "tasks": [{
                "text": "日本語タスク 🚀",
                "status": "pending",
                "created_at": "2026-02-09T10:00:00+00:00",
                "handled_at": None,
                "subjective_date": None,
                "note": None,
            }]
        }

        data.save_tasks(str(path), tasks_data)

        # Read it back
        with open(path, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        assert loaded["tasks"][0]["text"] == "日本語タスク 🚀"


class TestAddTask:
    """Test add_task function."""

    def test_add_task_returns_index(self):
        """Test that add_task returns correct index."""
        tasks_data = {"tasks": []}

        index = data.add_task(tasks_data, "First task")
        assert index == 0

        index = data.add_task(tasks_data, "Second task")
        assert index == 1

    def test_add_task_structure(self):
        """Test that add_task creates correct task structure."""
        tasks_data = {"tasks": []}

        data.add_task(tasks_data, "Test task")

        task = tasks_data["tasks"][0]
        assert task["text"] == "Test task"
        assert task["status"] == "pending"
        assert task["created_at"] is not None
        assert task["handled_at"] is None
        assert task["subjective_date"] is None
        assert task["note"] is None

    def test_add_task_status_pending(self):
        """Test that new tasks have 'pending' status."""
        tasks_data = {"tasks": []}

        data.add_task(tasks_data, "Test task")

        assert tasks_data["tasks"][0]["status"] == "pending"

    def test_add_task_nulls_set_correctly(self):
        """Test that handled fields are null for new tasks."""
        tasks_data = {"tasks": []}

        data.add_task(tasks_data, "Test task")

        task = tasks_data["tasks"][0]
        assert task["handled_at"] is None
        assert task["subjective_date"] is None
        assert task["note"] is None

    def test_add_task_timestamp_utc(self):
        """Test that created_at is UTC timestamp."""
        tasks_data = {"tasks": []}

        data.add_task(tasks_data, "Test task")

        created_at = tasks_data["tasks"][0]["created_at"]
        # Should be able to parse as ISO format
        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        assert dt.tzinfo is not None


class TestUpdateTask:
    """Test update_task function."""

    def test_update_task_valid_field(self, sample_tasks_data):
        """Test updating allowed field."""
        result = data.update_task(sample_tasks_data, 0, text="Updated text")

        assert result is True
        assert sample_tasks_data["tasks"][0]["text"] == "Updated text"

    def test_update_task_invalid_field(self, sample_tasks_data):
        """Test that invalid field raises ValueError."""
        with pytest.raises(ValueError, match="Invalid task fields"):
            data.update_task(sample_tasks_data, 0, invalid_field="bad")

    def test_update_task_nonexistent_index(self, sample_tasks_data):
        """Test updating non-existent index returns False."""
        result = data.update_task(sample_tasks_data, 999, text="Updated")

        assert result is False

    def test_update_task_multiple_fields(self, sample_tasks_data):
        """Test updating multiple fields at once."""
        result = data.update_task(
            sample_tasks_data,
            0,
            status="done",
            note="Completed",
            subjective_date="2026-02-09",
        )

        assert result is True
        task = sample_tasks_data["tasks"][0]
        assert task["status"] == "done"
        assert task["note"] == "Completed"
        assert task["subjective_date"] == "2026-02-09"

    def test_update_task_invalid_field_mixed(self, sample_tasks_data):
        """Test that mixed valid/invalid fields rejects all."""
        with pytest.raises(ValueError, match="Invalid task fields"):
            data.update_task(
                sample_tasks_data,
                0,
                text="Valid",
                invalid="Bad",
            )

        # Original should be unchanged
        assert sample_tasks_data["tasks"][0]["text"] == "Task one"


class TestDeleteTask:
    """Test delete_task function."""

    def test_delete_task_valid_index(self, sample_tasks_data):
        """Test deleting task by valid index."""
        original_count = len(sample_tasks_data["tasks"])

        result = data.delete_task(sample_tasks_data, 1)

        assert result is True
        assert len(sample_tasks_data["tasks"]) == original_count - 1

    def test_delete_task_invalid_index(self, sample_tasks_data):
        """Test that invalid index returns False."""
        result = data.delete_task(sample_tasks_data, 999)

        assert result is False

    def test_delete_task_shifts_indices(self, sample_tasks_data):
        """Test that deleting shifts subsequent indices."""
        # Task at index 2 before deletion
        task_text = sample_tasks_data["tasks"][2]["text"]

        data.delete_task(sample_tasks_data, 0)

        # Now at index 1
        assert sample_tasks_data["tasks"][1]["text"] == task_text


class TestGroupHandledTasks:
    """Test group_handled_tasks function."""

    def test_group_handled_tasks_empty(self):
        """Test grouping empty list."""
        result = data.group_handled_tasks([], include_unknown=True)

        assert result == []

    def test_group_handled_tasks_by_date(self):
        """Test that tasks are grouped by subjective_date."""
        tasks = [
            (0, {"subjective_date": "2026-02-09", "handled_at": "2026-02-09T10:00:00+00:00"}),
            (1, {"subjective_date": "2026-02-09", "handled_at": "2026-02-09T11:00:00+00:00"}),
            (2, {"subjective_date": "2026-02-08", "handled_at": "2026-02-08T10:00:00+00:00"}),
        ]

        result = data.group_handled_tasks(tasks, include_unknown=True)

        assert len(result) == 2
        dates = [date for date, _ in result]
        assert "2026-02-09" in dates
        assert "2026-02-08" in dates

    def test_group_handled_tasks_unknown(self):
        """Test handling of tasks with missing dates."""
        tasks = [
            (0, {"subjective_date": "2026-02-09", "handled_at": "2026-02-09T10:00:00+00:00"}),
            (1, {"subjective_date": None, "handled_at": "2026-02-08T10:00:00+00:00"}),
        ]

        result = data.group_handled_tasks(tasks, include_unknown=True)

        dates = [date for date, _ in result]
        assert "2026-02-09" in dates
        assert "unknown" in dates

    def test_group_handled_tasks_sort_dates_desc(self):
        """Test that dates are sorted descending."""
        tasks = [
            (0, {"subjective_date": "2026-02-07", "handled_at": "2026-02-07T10:00:00+00:00"}),
            (1, {"subjective_date": "2026-02-09", "handled_at": "2026-02-09T10:00:00+00:00"}),
            (2, {"subjective_date": "2026-02-08", "handled_at": "2026-02-08T10:00:00+00:00"}),
        ]

        result = data.group_handled_tasks(tasks, include_unknown=True)

        dates = [date for date, _ in result]
        assert dates == ["2026-02-09", "2026-02-08", "2026-02-07"]

    def test_group_handled_tasks_sort_within_date(self):
        """Test that tasks within date are sorted by handled_at ascending."""
        tasks = [
            (0, {"subjective_date": "2026-02-09", "handled_at": "2026-02-09T12:00:00+00:00"}),
            (1, {"subjective_date": "2026-02-09", "handled_at": "2026-02-09T10:00:00+00:00"}),
            (2, {"subjective_date": "2026-02-09", "handled_at": "2026-02-09T11:00:00+00:00"}),
        ]

        result = data.group_handled_tasks(tasks, include_unknown=True)

        # Get the tasks for 2026-02-09
        for date, date_tasks in result:
            if date == "2026-02-09":
                handled_times = [t["handled_at"] for _, t in date_tasks]
                assert handled_times == [
                    "2026-02-09T10:00:00+00:00",
                    "2026-02-09T11:00:00+00:00",
                    "2026-02-09T12:00:00+00:00",
                ]
                break
