"""TODO.md generation from task data."""

from pathlib import Path
from typing import Any

from tk import data

def sort_tasks(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    """Sort tasks into structure for rendering."""
    return data.group_tasks_for_display(tasks)


def generate_todo(tasks: list[dict[str, Any]], output_path: str) -> None:
    """Generate TODO.md from tasks.

    Args:
        tasks: List of task dictionaries
        output_path: Path to TODO.md

    Structure:
        # TODO

        - pending task

        ## History

        ### YYYY-MM-DD (descending dates)
        - ✅ done task (note if present)
        - ❌ cancelled task (note if present)

    Formatting:
    - Empty line after "# TODO"
    - If no pending tasks, show "No pending tasks."
    - History section only shown if there are handled tasks
    - Empty line after "## History"
    - File ends with empty line
    """
    sorted_data = sort_tasks(tasks)
    lines = ["# TODO", ""]

    # Pending section
    if sorted_data["pending"]:
        for task in sorted_data["pending"]:
            lines.append(f"- {task['text']}")
    else:
        lines.append("No pending tasks.")

    # Check if there are any handled tasks
    has_handled = any(sorted_data["done"]) or any(sorted_data["cancelled"])

    if not has_handled:
        # No history to show, just end with empty line
        lines.append("")
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return

    # History section (merge done and cancelled)
    lines.append("")
    lines.append("## History")
    lines.append("")

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
            status_emoji = "✅" if task["status"] == "done" else "❌"

            if note:
                lines.append(f"- {status_emoji} {text} => {note}")
            else:
                lines.append(f"- {status_emoji} {text}")

    # End with empty line
    lines.append("")

    # Write to file
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
