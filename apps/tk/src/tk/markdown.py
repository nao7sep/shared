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
            "declined": {
                "2026-01-30": [tasks sorted by handled_at asc]
            }
        }

    Sorting rules:
    - Pending: by created_at ascending (oldest first)
    - Done/Declined: grouped by subjective_date descending (newest date first),
      within each date group sorted by handled_at ascending (earliest first)
    """
    result = {
        "pending": [],
        "done": {},
        "declined": {}
    }

    for task in tasks:
        status = task["status"]

        if status == "pending":
            result["pending"].append(task)
        elif status in ("done", "declined"):
            # Group by subjective date
            date = task.get("subjective_date")
            if date:  # Skip if no subjective_date (shouldn't happen)
                if date not in result[status]:
                    result[status][date] = []
                result[status][date].append(task)

    # Sort pending by created_at ascending
    result["pending"].sort(key=lambda t: t["created_at"])

    # Sort done/declined: dates descending, within date handled_at ascending
    for status in ("done", "declined"):
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
        # Tasks

        ## Pending
        - [ ] task text

        ## Done
        ### YYYY-MM-DD (descending dates)
        - [x] task text (note if present)

        ## Declined
        ### YYYY-MM-DD (descending dates)
        - [~] task text (note if present)

    Formatting:
    - Pending: `- [ ] task text`
    - Done: `- [x] task text (note)` if note, else `- [x] task text`
    - Declined: `- [~] task text (note)` if note, else `- [~] task text`
    - Dates in descending order
    - Within date, tasks in ascending order by handled_at
    """
    sorted_data = sort_tasks(tasks)
    lines = ["# Tasks", ""]

    # Pending section
    lines.append("## Pending")
    if sorted_data["pending"]:
        for task in sorted_data["pending"]:
            lines.append(f"- [ ] {task['text']}")
    else:
        lines.append("")
    lines.append("")

    # Done section
    lines.append("## Done")
    if sorted_data["done"]:
        for date, date_tasks in sorted_data["done"]:
            lines.append(f"### {date}")
            for task in date_tasks:
                text = task["text"]
                note = task.get("note")
                if note:
                    lines.append(f"- [x] {text} ({note})")
                else:
                    lines.append(f"- [x] {text}")
            lines.append("")
    else:
        lines.append("")

    # Declined section
    lines.append("## Declined")
    if sorted_data["declined"]:
        for date, date_tasks in sorted_data["declined"]:
            lines.append(f"### {date}")
            for task in date_tasks:
                text = task["text"]
                note = task.get("note")
                if note:
                    lines.append(f"- [~] {text} ({note})")
                else:
                    lines.append(f"- [~] {text}")
            lines.append("")
    else:
        lines.append("")

    # Write to file
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w") as f:
        f.write("\n".join(lines))
