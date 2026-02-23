"""Compatibility facade for task data operations.

The concrete implementations now live in focused modules:
- tk.repository
- tk.task_schema
- tk.task_ops
- tk.task_queries
"""

from tk.repository import load_tasks, save_tasks
from tk.task_ops import add_task, delete_task, get_task_by_index, update_task
from tk.task_queries import group_handled_tasks, group_tasks_for_display
from tk.task_schema import validate_tasks_structure

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
