"""Task data API combining storage and query helpers.

This module is the primary import surface for task data operations used by the
rest of the application.
"""

from tk.storage import load_tasks, save_tasks
from tk.task_queries import group_handled_tasks, group_tasks_for_display


__all__ = [
    "load_tasks",
    "save_tasks",
    "group_tasks_for_display",
    "group_handled_tasks",
]
