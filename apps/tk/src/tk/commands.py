"""Command handlers for the tk CLI."""

from typing import Any
from datetime import datetime, timezone
import re

from tk import profile, data, subjective_date, markdown


def cmd_new(profile_path: str, session: dict[str, Any]) -> str:
    """Create new profile.

    Args:
        profile_path: Path where to save the profile
        session: Current session state (will be updated)

    Returns:
        Success message
    """
    prof = profile.create_profile(profile_path)
    session["profile_path"] = profile_path
    session["profile"] = prof

    # Create empty tasks file
    tasks_data = {"next_id": 1, "tasks": []}
    data.save_tasks(prof["data_path"], tasks_data)
    session["tasks"] = tasks_data

    # Generate empty TODO.md
    markdown.generate_todo([], prof["output_path"])

    # Clear last_list
    session["last_list"] = []

    return f"Profile created: {profile_path}"


def cmd_add(session: dict[str, Any], text: str) -> str:
    """Add new task.

    Args:
        session: Current session state
        text: Task text

    Returns:
        Success message
    """
    if not text.strip():
        raise ValueError("Task text cannot be empty")

    # Clear last_list (not a number-based command, but changes state)
    session["last_list"] = []

    # Add task
    task_id = data.add_task(session["tasks"], text)

    # Save
    data.save_tasks(session["profile"]["data_path"], session["tasks"])

    # Regenerate TODO.md
    markdown.generate_todo(session["tasks"]["tasks"], session["profile"]["output_path"])

    return f"Task #{task_id} added."


def cmd_list(session: dict[str, Any]) -> str:
    """List pending tasks.

    Args:
        session: Current session state

    Returns:
        Formatted list of tasks

    Updates session.last_list with [(display_num, task_id), ...]
    """
    pending = [t for t in session["tasks"]["tasks"] if t["status"] == "pending"]

    # Sort by created_at ascending
    pending.sort(key=lambda t: t["created_at"])

    if not pending:
        session["last_list"] = []
        return "No pending tasks."

    # Build output and last_list mapping
    lines = []
    last_list = []

    for i, task in enumerate(pending, start=1):
        lines.append(f"{i}. [ ] {task['text']}")
        last_list.append((i, task["id"]))

    session["last_list"] = last_list

    return "\n".join(lines)


def cmd_history(session: dict[str, Any], days: int | None = None) -> str:
    """List handled tasks (done or declined).

    Args:
        session: Current session state
        days: Optional number of days to show

    Returns:
        Formatted list of handled tasks

    Updates session.last_list with [(display_num, task_id), ...]
    """
    handled = [t for t in session["tasks"]["tasks"] if t["status"] in ("done", "declined")]

    if days is not None:
        # Filter by subjective_date (last N days)
        from datetime import date, timedelta
        cutoff = date.today() - timedelta(days=days - 1)
        handled = [
            t for t in handled
            if t.get("subjective_date") and t["subjective_date"] >= cutoff.isoformat()
        ]

    if not handled:
        session["last_list"] = []
        return "No handled tasks." if days is None else f"No handled tasks in last {days} days."

    # Group by subjective_date (descending), sort within group by handled_at (ascending)
    from collections import defaultdict
    by_date = defaultdict(list)

    for task in handled:
        date_str = task.get("subjective_date", "unknown")
        by_date[date_str].append(task)

    # Sort each group by handled_at
    for date_str in by_date:
        by_date[date_str].sort(key=lambda t: t.get("handled_at", ""))

    # Sort dates descending
    sorted_dates = sorted(by_date.keys(), reverse=True)

    # Build output
    lines = []
    last_list = []
    num = 1

    for date_str in sorted_dates:
        lines.append(date_str)
        for task in by_date[date_str]:
            status_char = "x" if task["status"] == "done" else "~"
            text = task["text"]
            note = task.get("note")

            if note:
                line = f"  {num}. [{status_char}] {text} ({note})"
            else:
                line = f"  {num}. [{status_char}] {text}"

            lines.append(line)
            last_list.append((num, task["id"]))
            num += 1

        lines.append("")  # Blank line between dates

    session["last_list"] = last_list

    return "\n".join(lines)


def cmd_done(session: dict[str, Any], num: int, note: str | None = None, date_str: str | None = None) -> str:
    """Mark task as done.

    Args:
        session: Current session state
        num: Task number from last list/history
        note: Optional note
        date_str: Optional subjective date (YYYY-MM-DD)

    Returns:
        Success message
    """
    return _handle_task(session, num, "done", note, date_str)


def cmd_decline(session: dict[str, Any], num: int, note: str | None = None, date_str: str | None = None) -> str:
    """Mark task as declined.

    Args:
        session: Current session state
        num: Task number from last list/history
        note: Optional note
        date_str: Optional subjective date (YYYY-MM-DD)

    Returns:
        Success message
    """
    return _handle_task(session, num, "declined", note, date_str)


def _handle_task(session: dict[str, Any], num: int, status: str, note: str | None, date_str: str | None) -> str:
    """Helper to handle a task (done or declined).

    Args:
        session: Current session state
        num: Task number from last list/history
        status: "done" or "declined"
        note: Optional note
        date_str: Optional subjective date (YYYY-MM-DD)

    Returns:
        Success message
    """
    # Check last_list exists
    if not session.get("last_list"):
        raise ValueError("Run 'list' or 'history' first")

    # Map num to task_id
    task_id = None
    for display_num, tid in session["last_list"]:
        if display_num == num:
            task_id = tid
            break

    if task_id is None:
        raise ValueError("Invalid task number")

    # Calculate subjective date
    if date_str:
        # Validate format
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
            raise ValueError("Invalid date format. Expected: YYYY-MM-DD")
        subj_date = date_str
    else:
        # Calculate from current time
        subj_date = subjective_date.get_current_subjective_date(
            session["profile"]["timezone"],
            session["profile"]["subjective_day_start"]
        )

    # Update task
    now_utc = datetime.now(timezone.utc).isoformat()
    updates = {
        "status": status,
        "handled_at": now_utc,
        "subjective_date": subj_date,
        "note": note
    }

    if not data.update_task(session["tasks"], task_id, **updates):
        raise ValueError("Task not found")

    # Save
    data.save_tasks(session["profile"]["data_path"], session["tasks"])

    # Regenerate TODO.md
    markdown.generate_todo(session["tasks"]["tasks"], session["profile"]["output_path"])

    # Clear last_list
    session["last_list"] = []

    return f"Task #{task_id} marked as {status}."


def cmd_edit(session: dict[str, Any], num: int, text: str) -> str:
    """Edit task text.

    Args:
        session: Current session state
        num: Task number from last list/history
        text: New task text

    Returns:
        Success message
    """
    # Check last_list exists
    if not session.get("last_list"):
        raise ValueError("Run 'list' or 'history' first")

    if not text.strip():
        raise ValueError("Task text cannot be empty")

    # Map num to task_id
    task_id = None
    for display_num, tid in session["last_list"]:
        if display_num == num:
            task_id = tid
            break

    if task_id is None:
        raise ValueError("Invalid task number")

    # Update task
    if not data.update_task(session["tasks"], task_id, text=text):
        raise ValueError("Task not found")

    # Save
    data.save_tasks(session["profile"]["data_path"], session["tasks"])

    # Regenerate TODO.md
    markdown.generate_todo(session["tasks"]["tasks"], session["profile"]["output_path"])

    # Clear last_list
    session["last_list"] = []

    return f"Task #{task_id} updated."


def cmd_delete(session: dict[str, Any], num: int) -> str:
    """Delete task permanently.

    Args:
        session: Current session state
        num: Task number from last list/history

    Returns:
        Success message
    """
    # Check last_list exists
    if not session.get("last_list"):
        raise ValueError("Run 'list' or 'history' first")

    # Map num to task_id
    task_id = None
    for display_num, tid in session["last_list"]:
        if display_num == num:
            task_id = tid
            break

    if task_id is None:
        raise ValueError("Invalid task number")

    # Delete task
    if not data.delete_task(session["tasks"], task_id):
        raise ValueError("Task not found")

    # Save
    data.save_tasks(session["profile"]["data_path"], session["tasks"])

    # Regenerate TODO.md
    markdown.generate_todo(session["tasks"]["tasks"], session["profile"]["output_path"])

    # Clear last_list
    session["last_list"] = []

    return f"Task #{task_id} deleted."


def cmd_sync(session: dict[str, Any]) -> str:
    """Regenerate TODO.md from current data.

    Args:
        session: Current session state

    Returns:
        Success message
    """
    markdown.generate_todo(session["tasks"]["tasks"], session["profile"]["output_path"])

    # Clear last_list
    session["last_list"] = []

    return "TODO.md regenerated."
