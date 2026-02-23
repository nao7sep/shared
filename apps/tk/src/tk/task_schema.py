"""Validation for persisted task JSON structure."""

from typing import Any


def validate_tasks_structure(data: dict[str, Any]) -> None:
    """Validate tasks data structure and task schemas."""
    if "tasks" not in data:
        raise ValueError("Invalid tasks file structure: missing 'tasks' key")

    if not isinstance(data["tasks"], list):
        raise ValueError("Invalid tasks file structure: 'tasks' must be an array")

    required_fields = {"text", "status", "created_at"}
    valid_statuses = {"pending", "done", "cancelled"}

    for i, task in enumerate(data["tasks"]):
        if not isinstance(task, dict):
            raise ValueError(f"Task {i} is not a valid object")

        missing = required_fields - set(task.keys())
        if missing:
            raise ValueError(f"Task {i} missing required fields: {', '.join(sorted(missing))}")

        if task["status"] not in valid_statuses:
            raise ValueError(f"Task {i} has invalid status: {task['status']}")
