"""CLI output formatting helpers.

Follows the shared CLI output formatting standards spec:
- One blank line between semantic segments.
- Explicit empty-state feedback.
- No colors or text decorations.
- No hard-wrapping.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from .models import Assignment, AssignmentStatus, Database, Group, Project, ProjectState, Task


def print_blank() -> None:
    """Print one blank line."""
    print()


def print_segment(lines: Iterable[str]) -> None:
    """Print a leading blank line, then each line in lines."""
    print()
    for line in lines:
        print(line)


def format_group(group: Group) -> str:
    return f"g{group.id}: {group.name}"


def format_project(project: Project, group: Group) -> str:
    state_label = f"[{project.state.value}]"
    return f"p{project.id}: {project.name} {state_label} (group: {group.name})"


def format_task(task: Task, db: Database) -> str:
    created = format_local_time(task.created_utc)
    if task.group_id is not None:
        group_label = _resolve_group_label(db, task.group_id)
    else:
        group_label = "all groups"
    return f"t{task.id}: {task.description} [created: {created}] [target: {group_label}]"


def format_assignment(
    assignment: Assignment, project: Project, task: Task
) -> str:
    status = assignment.status.value
    line = f"p{project.id}/{project.name} + t{task.id}/{task.description}: {status}"
    if assignment.comment:
        line += f" — {assignment.comment}"
    return line


def format_local_time(utc_iso: str) -> str:
    """Parse UTC ISO string, convert to local time, format as 'YYYY-MM-DD HH:MM:SS'."""
    # Handle both '+00:00' and 'Z' suffixes
    normalized = utc_iso.replace("Z", "+00:00")
    dt_utc = datetime.fromisoformat(normalized).astimezone(tz=None)
    return dt_utc.strftime("%Y-%m-%d %H:%M:%S")


def format_status_mark(status: AssignmentStatus) -> str:
    """Return a text mark for CLI display (not HTML)."""
    if status == AssignmentStatus.OK:
        return "ok"
    if status == AssignmentStatus.NAH:
        return "nah"
    return "pending"


def _resolve_group_label(db: Database, group_id: int) -> str:
    for g in db.groups:
        if g.id == group_id:
            return g.name
    return f"g{group_id} (not found)"


def describe_project_state(state: ProjectState) -> str:
    return state.value
