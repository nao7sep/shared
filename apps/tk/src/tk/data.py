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
        with open(task_path, "r", encoding="utf-8") as f:
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

    with open(task_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


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


def group_tasks_for_display(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    """Group and sort tasks for display layers.

    Returns:
        {
            "pending": [tasks sorted by created_at asc],
            "done": [(date, [tasks sorted by handled_at asc]), ...],
            "cancelled": [(date, [tasks sorted by handled_at asc]), ...],
        }
    """
    result: dict[str, Any] = {
        "pending": [],
        "done": [],
        "cancelled": [],
    }

    for task in tasks:
        if task["status"] == "pending":
            result["pending"].append(task)

    result["pending"].sort(key=lambda t: t["created_at"])

    for status in ("done", "cancelled"):
        handled_with_indices = [
            (i, task)
            for i, task in enumerate(tasks)
            if task["status"] == status
        ]
        grouped = group_handled_tasks(handled_with_indices, include_unknown=True)
        result[status] = [(date, [task for _, task in date_tasks]) for date, date_tasks in grouped]

    return result


def group_handled_tasks(
    handled_with_indices: list[tuple[int, dict[str, Any]]],
    *,
    include_unknown: bool,
) -> list[tuple[str, list[tuple[int, dict[str, Any]]]]]:
    """Group handled tasks by subjective date and sort deterministically.

    Sorting:
    - dates descending
    - tasks within date by handled_at ascending
    """
    grouped: dict[str, list[tuple[int, dict[str, Any]]]] = {}

    for array_index, task in handled_with_indices:
        date = task.get("subjective_date")
        if not date:
            if not include_unknown:
                continue
            date = "unknown"

        if date not in grouped:
            grouped[date] = []
        grouped[date].append((array_index, task))

    for date in grouped:
        grouped[date].sort(key=lambda x: x[1].get("handled_at", ""))

    known = sorted(
        [(date, items) for date, items in grouped.items() if date != "unknown"],
        key=lambda x: x[0],
        reverse=True,
    )
    if "unknown" in grouped:
        known.append(("unknown", grouped["unknown"]))
    return known
