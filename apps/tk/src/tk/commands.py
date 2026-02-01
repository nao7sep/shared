"""Command handlers for the tk CLI."""

from typing import Any
from datetime import datetime, timezone
import re

from tk import profile, data, subjective_date, markdown


def _sync_if_auto(session: dict[str, Any]) -> None:
    """Regenerate TODO.md if auto_sync is enabled.

    Args:
        session: Current session state with profile and tasks
    """
    if session.get("profile", {}).get("auto_sync", True):
        markdown.generate_todo(
            session["tasks"]["tasks"],
            session["profile"]["output_path"]
        )


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
    tasks_data = {"tasks": []}
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
    data.add_task(session["tasks"], text)

    # Save
    data.save_tasks(session["profile"]["data_path"], session["tasks"])

    # Regenerate TODO.md if auto_sync enabled
    _sync_if_auto(session)

    return "Task added."


def cmd_list(session: dict[str, Any]) -> str:
    """List pending tasks.

    Args:
        session: Current session state

    Returns:
        Formatted list of tasks

    Updates session.last_list with [(display_num, array_index), ...]
    """
    all_tasks = session["tasks"]["tasks"]

    # Find pending tasks and their indices
    pending_with_indices = [
        (i, task) for i, task in enumerate(all_tasks) if task["status"] == "pending"
    ]

    # Sort by created_at ascending
    pending_with_indices.sort(key=lambda x: x[1]["created_at"])

    if not pending_with_indices:
        session["last_list"] = []
        return "No pending tasks."

    # Build output and last_list mapping
    lines = []
    last_list = []

    # Calculate padding width based on total number of tasks
    total_count = len(pending_with_indices)
    num_width = len(str(total_count))

    for display_num, (array_index, task) in enumerate(pending_with_indices, start=1):
        # Right-align the number for vertical alignment
        padded_num = str(display_num).rjust(num_width)
        lines.append(f"{padded_num}. [ ] {task['text']}")
        last_list.append((display_num, array_index))

    session["last_list"] = last_list

    return "\n".join(lines)


def cmd_history(session: dict[str, Any], days: int | None = None) -> str:
    """List handled tasks (done or cancelled).

    Args:
        session: Current session state
        days: Optional number of days to show

    Returns:
        Formatted list of handled tasks

    Updates session.last_list with [(display_num, array_index), ...]
    """
    all_tasks = session["tasks"]["tasks"]

    # Find handled tasks and their indices
    handled_with_indices = [
        (i, task) for i, task in enumerate(all_tasks) if task["status"] in ("done", "cancelled")
    ]

    if days is not None:
        # Filter by subjective_date (last N days)
        from datetime import date, timedelta
        cutoff = date.today() - timedelta(days=days - 1)
        handled_with_indices = [
            (i, t) for i, t in handled_with_indices
            if t.get("subjective_date") and t["subjective_date"] >= cutoff.isoformat()
        ]

    if not handled_with_indices:
        session["last_list"] = []
        return "No handled tasks." if days is None else f"No handled tasks in last {days} days."

    # Group by subjective_date (descending), sort within group by handled_at (ascending)
    from collections import defaultdict
    by_date = defaultdict(list)

    for array_index, task in handled_with_indices:
        date_str = task.get("subjective_date", "unknown")
        by_date[date_str].append((array_index, task))

    # Sort each group by handled_at
    for date_str in by_date:
        by_date[date_str].sort(key=lambda x: x[1].get("handled_at", ""))

    # Sort dates descending
    sorted_dates = sorted(by_date.keys(), reverse=True)

    # Calculate total count for padding
    total_count = sum(len(by_date[date_str]) for date_str in sorted_dates)
    num_width = len(str(total_count))

    # Build output
    lines = []
    last_list = []
    display_num = 1

    for idx, date_str in enumerate(sorted_dates):
        lines.append(date_str)
        for array_index, task in by_date[date_str]:
            status_char = "x" if task["status"] == "done" else "~"
            text = task["text"]
            note = task.get("note")

            # Right-align the number for vertical alignment
            padded_num = str(display_num).rjust(num_width)

            if note:
                line = f"  {padded_num}. [{status_char}] {text} ({note})"
            else:
                line = f"  {padded_num}. [{status_char}] {text}"

            lines.append(line)
            last_list.append((display_num, array_index))
            display_num += 1

        # Add blank line between groups (not after the last one)
        if idx < len(sorted_dates) - 1:
            lines.append("")

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


def cmd_cancel(session: dict[str, Any], num: int, note: str | None = None, date_str: str | None = None) -> str:
    """Mark task as cancelled.

    Args:
        session: Current session state
        num: Task number from last list/history
        note: Optional note
        date_str: Optional subjective date (YYYY-MM-DD)

    Returns:
        Success message
    """
    return _handle_task(session, num, "cancelled", note, date_str)


def _handle_task(session: dict[str, Any], num: int, status: str, note: str | None, date_str: str | None, interactive: bool = True) -> str:
    """Helper to handle a task (done or cancelled).

    Args:
        session: Current session state
        num: Task number from last list/history
        status: "done" or "cancelled"
        note: Optional note
        date_str: Optional subjective date (YYYY-MM-DD)
        interactive: If True, prompt for confirmation and missing fields

    Returns:
        Success message
    """
    # Check last_list exists
    if not session.get("last_list"):
        raise ValueError("Run 'list' or 'history' first")

    # Map num to array index
    array_index = None
    for display_num, idx in session["last_list"]:
        if display_num == num:
            array_index = idx
            break

    if array_index is None:
        raise ValueError("Invalid task number")

    # Get the task to show in confirmation
    task = data.get_task_by_index(session["tasks"], array_index)
    if not task:
        raise ValueError("Task not found")

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

    # Interactive confirmation if enabled
    if interactive:
        try:
            print(f"Task: {task['text']}")
            print(f"Will be marked as: {status}")
            print(f"Subjective date: {subj_date}")
            print("(Press Ctrl+C to cancel)")

            # Prompt for note if not provided
            if note is None:
                note_input = input("Note (press Enter to skip): ").strip()
                note = note_input if note_input else None

            # Prompt for date override if not provided
            if not date_str:
                date_input = input(f"Date override (press Enter to use {subj_date}): ").strip()
                if date_input:
                    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_input):
                        raise ValueError("Invalid date format. Expected: YYYY-MM-DD")
                    subj_date = date_input

        except KeyboardInterrupt:
            print()  # New line after ^C
            return "Cancelled."

    # Update task
    now_utc = datetime.now(timezone.utc).isoformat()
    updates = {
        "status": status,
        "handled_at": now_utc,
        "subjective_date": subj_date,
        "note": note
    }

    if not data.update_task(session["tasks"], array_index, **updates):
        raise ValueError("Task not found")

    # Save
    data.save_tasks(session["profile"]["data_path"], session["tasks"])

    # Regenerate TODO.md if auto_sync enabled
    _sync_if_auto(session)

    # Clear last_list
    session["last_list"] = []

    return f"Task marked as {status}."


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

    # Map num to array index
    array_index = None
    for display_num, idx in session["last_list"]:
        if display_num == num:
            array_index = idx
            break

    if array_index is None:
        raise ValueError("Invalid task number")

    # Update task
    if not data.update_task(session["tasks"], array_index, text=text):
        raise ValueError("Task not found")

    # Save
    data.save_tasks(session["profile"]["data_path"], session["tasks"])

    # Regenerate TODO.md if auto_sync enabled
    _sync_if_auto(session)

    # Clear last_list
    session["last_list"] = []

    return "Task updated."


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

    # Map num to array index
    array_index = None
    for display_num, idx in session["last_list"]:
        if display_num == num:
            array_index = idx
            break

    if array_index is None:
        raise ValueError("Invalid task number")

    # Get task for confirmation
    task = data.get_task_by_index(session["tasks"], array_index)
    if not task:
        raise ValueError("Task not found")

    # Confirm deletion
    print(f"Task: {task['text']}")
    print(f"Status: {task['status']}")
    confirm = input("Delete permanently? (yes/N): ").strip().lower()
    if confirm != "yes":
        return "Deletion cancelled."

    # Delete task
    if not data.delete_task(session["tasks"], array_index):
        raise ValueError("Task not found")

    # Save
    data.save_tasks(session["profile"]["data_path"], session["tasks"])

    # Regenerate TODO.md if auto_sync enabled
    _sync_if_auto(session)

    # Clear last_list
    session["last_list"] = []

    return "Task deleted."


def cmd_note(session: dict[str, Any], num: int, note: str | None = None) -> str:
    """Set, update, or remove note on a task.

    Args:
        session: Current session state
        num: Task number from last list/history
        note: Note text (or None to remove)

    Returns:
        Success message
    """
    # Check last_list exists
    if not session.get("last_list"):
        raise ValueError("Run 'list' or 'history' first")

    # Map num to array index
    array_index = None
    for display_num, idx in session["last_list"]:
        if display_num == num:
            array_index = idx
            break

    if array_index is None:
        raise ValueError("Invalid task number")

    # Update task note
    if not data.update_task(session["tasks"], array_index, note=note):
        raise ValueError("Task not found")

    # Save
    data.save_tasks(session["profile"]["data_path"], session["tasks"])

    # Regenerate TODO.md if auto_sync enabled
    _sync_if_auto(session)

    # Clear last_list
    session["last_list"] = []

    if note:
        return "Note updated."
    else:
        return "Note removed."


def cmd_date(session: dict[str, Any], num: int, date_str: str) -> str:
    """Change subjective handling date on a task.

    Args:
        session: Current session state
        num: Task number from last list/history
        date_str: Subjective date in YYYY-MM-DD format

    Returns:
        Success message
    """
    # Check last_list exists
    if not session.get("last_list"):
        raise ValueError("Run 'list' or 'history' first")

    # Map num to array index
    array_index = None
    for display_num, idx in session["last_list"]:
        if display_num == num:
            array_index = idx
            break

    if array_index is None:
        raise ValueError("Invalid task number")

    # Get task to check if it's handled
    task = data.get_task_by_index(session["tasks"], array_index)
    if not task:
        raise ValueError("Task not found")

    # Only allow changing date on handled tasks
    if task["status"] == "pending":
        raise ValueError("Cannot set date on pending task. Mark it done or cancelled first.")

    # Validate date format
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        raise ValueError("Invalid date format. Expected: YYYY-MM-DD")

    # Update subjective_date
    if not data.update_task(session["tasks"], array_index, subjective_date=date_str):
        raise ValueError("Task not found")

    # Save
    data.save_tasks(session["profile"]["data_path"], session["tasks"])

    # Regenerate TODO.md if auto_sync enabled
    _sync_if_auto(session)

    # Clear last_list
    session["last_list"] = []

    return f"Subjective date updated to {date_str}."


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
