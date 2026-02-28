"""TODO.md generation from task data."""

from pathlib import Path

from tk import data
from tk.models import Task, TaskStatus

_DONE_STATUS = TaskStatus.DONE.value


def _write_todo(lines: list[str], output_path: str) -> None:
    """Write generated TODO.md content to disk."""
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def generate_todo(tasks: list[Task], output_path: str) -> None:
    """Generate TODO.md from tasks.

    Args:
        tasks: List of Task models
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
    grouped = data.group_tasks_for_display(tasks)
    lines = ["# TODO", ""]

    # Pending section
    if grouped.pending:
        for task in grouped.pending:
            lines.append(f"- {task.text}")
    else:
        lines.append("No pending tasks.")

    # Check if there are any handled tasks
    has_handled = bool(grouped.done) or bool(grouped.cancelled)

    if not has_handled:
        # No history to show, just end with empty line
        lines.append("")
        _write_todo(lines, output_path)
        return

    # History section (merge done and cancelled)
    lines.append("")
    lines.append("## History")
    lines.append("")

    # Merge done and cancelled by date
    all_dates: dict[str, list[Task]] = {}

    for date, date_tasks in grouped.done:
        if date not in all_dates:
            all_dates[date] = []
        all_dates[date].extend(date_tasks)

    for date, date_tasks in grouped.cancelled:
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

        # Sort tasks within date by handled_utc.
        date_tasks = sorted(all_dates[date], key=lambda t: t.handled_utc or "")

        for task in date_tasks:
            text = task.text
            note = task.note
            status_emoji = "✅" if task.status == _DONE_STATUS else "❌"

            if note:
                lines.append(f"- {status_emoji} {text} => {note}")
            else:
                lines.append(f"- {status_emoji} {text}")

    # End with empty line
    lines.append("")
    _write_todo(lines, output_path)
