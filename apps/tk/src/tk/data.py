"""Task data API combining storage, CRUD, and query helpers.

This module is the primary import surface for task data operations used by the
rest of the application.
"""

from tk.models import TaskStore
from tk.storage import load_tasks, save_tasks, validate_tasks_structure
from tk.task_queries import group_handled_tasks, group_tasks_for_display


def add_task(tasks_data: TaskStore, text: str) -> int:
    """Add a new task and return its array index."""
    return tasks_data.add_task(text)


def get_task_by_index(tasks_data: TaskStore, index: int):
    """Return task by array index."""
    return tasks_data.get_task_by_index(index)


def update_task(tasks_data: TaskStore, index: int, **updates) -> bool:
    """Update task fields by array index."""
    return tasks_data.update_task(index, **updates)


def delete_task(tasks_data: TaskStore, index: int) -> bool:
    """Delete task by array index."""
    return tasks_data.delete_task(index)


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
