"""Task data API combining storage, CRUD, and query helpers.

This module is the primary import surface for task data operations used by the
rest of the application.
"""

from datetime import datetime, timezone
from typing import Any

from tk.storage import load_tasks, save_tasks, validate_tasks_structure
from tk.task_queries import group_handled_tasks, group_tasks_for_display


def _tasks_list(data: dict[str, Any] | Any) -> list[Any]:
    """Return mutable task list from a dict payload or task-store object."""
    if hasattr(data, "tasks"):
        return data.tasks  # type: ignore[return-value]
    return data["tasks"]


def add_task(data: dict[str, Any] | Any, text: str) -> int:
    """Add a new task and return its array index."""
    if hasattr(data, "add_task") and callable(data.add_task):
        return data.add_task(text)

    tasks = _tasks_list(data)
    now_utc = datetime.now(timezone.utc).isoformat()
    task = {
        "text": text,
        "status": "pending",
        "created_at": now_utc,
        "handled_at": None,
        "subjective_date": None,
        "note": None,
    }
    tasks.append(task)
    return len(tasks) - 1


def get_task_by_index(data: dict[str, Any] | Any, index: int) -> Any | None:
    """Return task by array index."""
    if hasattr(data, "get_task_by_index") and callable(data.get_task_by_index):
        return data.get_task_by_index(index)

    tasks = _tasks_list(data)
    if 0 <= index < len(tasks):
        return tasks[index]
    return None


def update_task(data: dict[str, Any] | Any, index: int, **updates: Any) -> bool:
    """Update task fields by array index."""
    if hasattr(data, "update_task") and callable(data.update_task):
        return data.update_task(index, **updates)

    allowed_fields = {"text", "status", "handled_at", "subjective_date", "note"}
    invalid_fields = set(updates.keys()) - allowed_fields
    if invalid_fields:
        raise ValueError(f"Invalid task fields: {', '.join(sorted(invalid_fields))}")

    task = get_task_by_index(data, index)
    if task is None:
        return False

    for key, value in updates.items():
        task[key] = value
    return True


def delete_task(data: dict[str, Any] | Any, index: int) -> bool:
    """Delete task by array index."""
    if hasattr(data, "delete_task") and callable(data.delete_task):
        return data.delete_task(index)

    tasks = _tasks_list(data)
    if 0 <= index < len(tasks):
        tasks.pop(index)
        return True
    return False

__all__ = [
    "validate_tasks_structure",
    "load_tasks",
    "save_tasks",
    "add_task",
    "get_task_by_index",
    "update_task",
    "delete_task",
    "group_tasks_for_display",
    "group_handled_tasks",
]
