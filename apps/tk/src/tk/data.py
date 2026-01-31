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
        "next_id": 1,
        "tasks": []
    }
    """
    task_path = Path(path)

    if not task_path.exists():
        # Create directory if needed
        task_path.parent.mkdir(parents=True, exist_ok=True)
        return {"next_id": 1, "tasks": []}

    try:
        with open(task_path, "r") as f:
            data = json.load(f)

        # Validate structure
        if "next_id" not in data or "tasks" not in data:
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
        New task ID

    Task is created with:
    - id: next_id (then incremented)
    - text: provided text
    - status: "pending"
    - created_at: current UTC time
    - handled_at: null
    - subjective_date: null
    - note: null
    """
    task_id = data["next_id"]
    now_utc = datetime.now(timezone.utc).isoformat()

    task = {
        "id": task_id,
        "text": text,
        "status": "pending",
        "created_at": now_utc,
        "handled_at": None,
        "subjective_date": None,
        "note": None
    }

    data["tasks"].append(task)
    data["next_id"] += 1

    return task_id


def get_task_by_id(data: dict[str, Any], task_id: int) -> dict[str, Any] | None:
    """Find task by ID.

    Args:
        data: Tasks data structure
        task_id: Task ID to find

    Returns:
        Task dict or None if not found
    """
    for task in data["tasks"]:
        if task["id"] == task_id:
            return task
    return None


def update_task(data: dict[str, Any], task_id: int, **updates) -> bool:
    """Update task fields.

    Args:
        data: Tasks data structure
        task_id: Task ID to update
        **updates: Fields to update

    Returns:
        True if task was found and updated, False otherwise
    """
    task = get_task_by_id(data, task_id)
    if task is None:
        return False

    for key, value in updates.items():
        task[key] = value

    return True


def delete_task(data: dict[str, Any], task_id: int) -> bool:
    """Remove task from list.

    Args:
        data: Tasks data structure
        task_id: Task ID to delete

    Returns:
        True if task was found and deleted, False otherwise

    Note: IDs are never reused - gaps are fine
    """
    for i, task in enumerate(data["tasks"]):
        if task["id"] == task_id:
            data["tasks"].pop(i)
            return True
    return False
