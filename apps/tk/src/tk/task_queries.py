"""Task grouping and read-model helpers for presentation layers."""

from typing import Any


def group_tasks_for_display(tasks: list[Any]) -> dict[str, Any]:
    """Group and sort tasks for TODO/history display."""
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
    handled_with_indices: list[tuple[int, Any]],
    *,
    include_unknown: bool,
) -> list[tuple[str, list[tuple[int, Any]]]]:
    """Group handled tasks by subjective date with deterministic ordering."""
    grouped: dict[str, list[tuple[int, Any]]] = {}

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
