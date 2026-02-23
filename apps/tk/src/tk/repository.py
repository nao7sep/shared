"""Task file I/O operations."""

import json
from pathlib import Path
from typing import Any

from tk.task_schema import validate_tasks_structure


def load_tasks(path: str) -> dict[str, Any]:
    """Load tasks from JSON file."""
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
    """Save tasks to JSON file."""
    payload = data.to_dict() if hasattr(data, "to_dict") else data

    task_path = Path(path)
    task_path.parent.mkdir(parents=True, exist_ok=True)

    with open(task_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
