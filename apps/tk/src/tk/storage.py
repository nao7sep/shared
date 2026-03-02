"""Task persistence and persisted-structure validation."""

import json
from pathlib import Path

from tk.errors import StorageError
from tk.models import TaskStore


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

        return TaskStore.from_dict(data)
    except json.JSONDecodeError as e:
        raise StorageError(f"Invalid JSON in tasks file: {e}") from e
    except ValueError as e:
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
