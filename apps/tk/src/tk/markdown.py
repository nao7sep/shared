"""TODO.md generation from task data."""

from typing import Any
from pathlib import Path


def sort_tasks(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    """Sort tasks into structure for rendering.

    Args:
        tasks: List of task dictionaries

    Returns:
        Dictionary with structure:
        {
            "pending": [tasks sorted by created_at asc],
            "done": {
                "2026-01-31": [tasks sorted by handled_at asc],
                "2026-01-30": [tasks sorted by handled_at asc]
            },
            "cancelled": {
                "2026-01-30": [tasks sorted by handled_at asc]
            }
        }

    Sorting rules:
    - Pending: by created_at ascending (oldest first)
    - Done/Cancelled: grouped by subjective_date descending (newest date first),
      within each date group sorted by handled_at ascending (earliest first)
    """
    result = {
        "pending": [],
        "done": {},
        "cancelled": {}
    }

    for task in tasks:
        status = task["status"]

        if status == "pending":
            result["pending"].append(task)
        elif status in ("done", "cancelled"):
            # Group by subjective date
            date = task.get("subjective_date")
            if date:  # Skip if no subjective_date (shouldn't happen)
                if date not in result[status]:
                    result[status][date] = []
                result[status][date].append(task)

    # Sort pending by created_at ascending
    result["pending"].sort(key=lambda t: t["created_at"])

    # Sort done/cancelled: dates descending, within date handled_at ascending
    for status in ("done", "cancelled"):
        # Sort each date group by handled_at ascending
        for date in result[status]:
            result[status][date].sort(key=lambda t: t.get("handled_at", ""))

        # Convert to list of (date, tasks) sorted by date descending
        result[status] = sorted(
            result[status].items(),
            key=lambda x: x[0],
            reverse=True
        )

    return result


def generate_todo(tasks: list[dict[str, Any]], output_path: str) -> None:
    """Generate TODO.md from tasks.

    Args:
        tasks: List of task dictionaries
        output_path: Path to TODO.md

    Structure:
        # TODO
        - [ ] pending task

        ## History
        ### YYYY-MM-DD (descending dates)
        - [x] done task (note if present)
        - [~] cancelled task (note if present)

    Formatting:
    - Pending: `- [ ] task text` (no heading, just the list)
    - History: merged done and cancelled tasks by date
    - Dates in descending order
    - Within date, tasks in ascending order by handled_at
    - Empty line between date groups, not between date heading and tasks
    """
    sorted_data = sort_tasks(tasks)
    lines = ["# TODO"]

    # Pending section (no heading, just tasks)
    if sorted_data["pending"]:
        for task in sorted_data["pending"]:
            lines.append(f"- [ ] {task['text']}")

    # History section (merge done and cancelled)
    lines.append("")
    lines.append("## History")

    # Merge done and cancelled by date
    all_dates = {}

    # Add done tasks
    for date, date_tasks in sorted_data["done"]:
        if date not in all_dates:
            all_dates[date] = []
        all_dates[date].extend(date_tasks)

    # Add cancelled tasks
    for date, date_tasks in sorted_data["cancelled"]:
        if date not in all_dates:
            all_dates[date] = []
        all_dates[date].extend(date_tasks)

    # Sort dates descending
    sorted_dates = sorted(all_dates.keys(), reverse=True)

    for idx, date in enumerate(sorted_dates):
        # Add empty line before date heading (except for first one after "## History")
        if idx > 0:
            lines.append("")

        lines.append(f"### {date}")

        # Sort tasks within date by handled_at
        date_tasks = sorted(all_dates[date], key=lambda t: t.get("handled_at", ""))

        for task in date_tasks:
            text = task["text"]
            note = task.get("note")
            status_char = "x" if task["status"] == "done" else "~"

            if note:
                lines.append(f"- [{status_char}] {text} ({note})")
            else:
                lines.append(f"- [{status_char}] {text}")

    # Write to file
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w") as f:
        f.write("\n".join(lines))
