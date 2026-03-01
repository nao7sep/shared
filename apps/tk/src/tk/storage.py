"""Task persistence and persisted-structure validation."""

import json
from pathlib import Path
from typing import Any

from tk.errors import StorageError, ValidationError
from tk.models import TaskStatus, TaskStore

_VALID_TASK_STATUSES = {status.value for status in TaskStatus}


def validate_tasks_structure(data: dict[str, Any]) -> None:
    """Validate persisted task payload structure."""
    if "tasks" not in data:
        raise ValidationError("Invalid tasks file structure: missing 'tasks' key")

    if not isinstance(data["tasks"], list):
        raise ValidationError("Invalid tasks file structure: 'tasks' must be an array")

    for i, task in enumerate(data["tasks"]):
        if not isinstance(task, dict):
            raise ValidationError(f"Task {i} is not a valid object")

        required_fields = {"text", "status"}
        missing = required_fields - set(task.keys())
        if "created_utc" not in task:
            missing = set(missing)
            missing.add("created_utc")
        if missing:
            raise ValidationError(f"Task {i} missing required fields: {', '.join(sorted(missing))}")

        if task["status"] not in _VALID_TASK_STATUSES:
            raise ValidationError(f"Task {i} has invalid status: {task['status']}")


def load_tasks(path: str) -> TaskStore:
    """Load tasks from JSON and validate structure."""
    task_path = Path(path)

    if not task_path.exists():
        try:
            task_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise StorageError(f"Failed to create task directory: {task_path.parent}: {e}") from e
        return TaskStore()

    try:
        with open(task_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        validate_tasks_structure(data)
        return TaskStore.from_dict(data)
    except json.JSONDecodeError as e:
        raise StorageError(f"Invalid JSON in tasks file: {e}") from e
    except ValidationError as e:
        raise StorageError(str(e)) from e
    except OSError as e:
        raise StorageError(f"Failed to read tasks file: {task_path}: {e}") from e


def save_tasks(path: str, tasks_data: TaskStore) -> None:
    """Save tasks payload to JSON."""
    task_path = Path(path)
    try:
        task_path.parent.mkdir(parents=True, exist_ok=True)

        with open(task_path, "w", encoding="utf-8") as f:
            json.dump(tasks_data.to_dict(), f, indent=2, ensure_ascii=False)
    except OSError as e:
        raise StorageError(f"Failed to save tasks file: {task_path}: {e}") from e
