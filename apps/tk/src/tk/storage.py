"""Task persistence and persisted-structure validation."""

import json
from pathlib import Path
from typing import Any


def validate_tasks_structure(data: dict[str, Any]) -> None:
    """Validate persisted task payload structure."""
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


def load_tasks(path: str) -> dict[str, Any]:
    """Load tasks from JSON and validate structure."""
    task_path = Path(path)

    if not task_path.exists():
        task_path.parent.mkdir(parents=True, exist_ok=True)
        return {"tasks": []}

    try:
        with open(task_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        validate_tasks_structure(data)
        return data
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in tasks file: {e}")


def save_tasks(path: str, data: dict[str, Any] | Any) -> None:
    """Save tasks payload to JSON."""
    payload = data.to_dict() if hasattr(data, "to_dict") else data

    task_path = Path(path)
    task_path.parent.mkdir(parents=True, exist_ok=True)

    with open(task_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
