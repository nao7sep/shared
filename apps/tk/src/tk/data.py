"""Task data operations: load, save, and CRUD operations."""

import json
from pathlib import Path
from typing import Any
from datetime import datetime, timezone


def load_tasks(path: str) -> dict[str, Any]:
    """Load tasks from JSON file.

    Args:
        path: Path to tasks.json

    Returns:
        Tasks data structure

    If file doesn't exist, returns empty structure:
    {
        "tasks": []
    }
    """
    task_path = Path(path)

    if not task_path.exists():
        # Create directory if needed
        task_path.parent.mkdir(parents=True, exist_ok=True)
        return {"tasks": []}

    try:
        with open(task_path, "r") as f:
            data = json.load(f)

        # Validate structure
        if "tasks" not in data:
            raise ValueError("Invalid tasks file structure")

        return data
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in tasks file: {e}")


def save_tasks(path: str, data: dict[str, Any]) -> None:
    """Save tasks to JSON file.

    Args:
        path: Path to tasks.json
        data: Tasks data structure
    """
    task_path = Path(path)

    # Create directory if needed
    task_path.parent.mkdir(parents=True, exist_ok=True)

    with open(task_path, "w") as f:
        json.dump(data, f, indent=2)


def add_task(data: dict[str, Any], text: str) -> int:
    """Add new task to data.

    Args:
        data: Tasks data structure
        text: Task text

    Returns:
        Array index of the new task

    Task is created with:
    - text: provided text
    - status: "pending"
    - created_at: current UTC time
    - handled_at: null
    - subjective_date: null
    - note: null
    """
    now_utc = datetime.now(timezone.utc).isoformat()

    task = {
        "text": text,
        "status": "pending",
        "created_at": now_utc,
        "handled_at": None,
        "subjective_date": None,
        "note": None
    }

    data["tasks"].append(task)

    # Return the index of the newly added task
    return len(data["tasks"]) - 1


def get_task_by_index(data: dict[str, Any], index: int) -> dict[str, Any] | None:
    """Get task by array index.

    Args:
        data: Tasks data structure
        index: Array index

    Returns:
        Task dict or None if index is out of range
    """
    if 0 <= index < len(data["tasks"]):
        return data["tasks"][index]
    return None


def update_task(data: dict[str, Any], index: int, **updates) -> bool:
    """Update task fields.

    Args:
        data: Tasks data structure
        index: Array index of task to update
        **updates: Fields to update

    Returns:
        True if task was found and updated, False otherwise
    """
    task = get_task_by_index(data, index)
    if task is None:
        return False

    for key, value in updates.items():
        task[key] = value

    return True


def delete_task(data: dict[str, Any], index: int) -> bool:
    """Remove task from list.

    Args:
        data: Tasks data structure
        index: Array index of task to delete

    Returns:
        True if task was found and deleted, False otherwise
    """
    if 0 <= index < len(data["tasks"]):
        data["tasks"].pop(index)
        return True
    return False
