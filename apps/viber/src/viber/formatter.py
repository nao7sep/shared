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

_LOCAL_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def print_banner(lines: Iterable[str]) -> None:
    """Print initial banner segment (no leading blank), then one trailing blank."""
    for line in lines:
        print(line)
    print()


def print_blank() -> None:
    """Print one blank line."""
    print()


def print_segment(
    lines: Iterable[str],
    *,
    leading_blank: bool = False,
    trailing_blank: bool = True,
) -> None:
    """Print a semantic output segment with configurable blank-line boundaries."""
    if leading_blank:
        print()
    for line in lines:
        print(line)
    if trailing_blank:
        print()


def format_group_ref(group: Group) -> str:
    return f"{group.name} (g{group.id})"


def format_project_ref(project: Project) -> str:
    return f"{project.name} (p{project.id})"


def format_task_ref(task: Task) -> str:
    return f"{task.description} (t{task.id})"


def format_group(group: Group) -> str:
    return format_group_ref(group)


def format_project(project: Project, group: Group) -> str:
    created = format_local_time(project.created_utc)
    return (
        f"{format_project_ref(project)}"
        f" | {format_group_ref(group)}"
        f" | {project.state.value}"
        f" | {created}"
    )


def format_task(task: Task, db: Database) -> str:
    created = format_local_time(task.created_utc)
    if task.group_id is not None:
        group_label = _resolve_group_label(db, task.group_id)
    else:
        group_label = "all groups"
    return f"{format_task_ref(task)} | {group_label} | {created}"


def format_assignment(
    assignment: Assignment, project: Project, task: Task
) -> str:
    status = assignment.status.value
    handled = (
        format_local_time(assignment.handled_utc)
        if assignment.handled_utc is not None
        else "-"
    )
    comment = assignment.comment if assignment.comment else "-"
    return (
        f"{format_project_ref(project)}"
        f" | {format_task_ref(task)}"
        f" | {status}"
        f" | {handled}"
        f" | {comment}"
    )


def format_local_time(utc_iso: str) -> str:
    """Parse UTC ISO string, convert to local time, format as 'YYYY-MM-DD HH:MM:SS'."""
    # Handle both '+00:00' and 'Z' suffixes
    normalized = utc_iso.replace("Z", "+00:00")
    dt_utc = datetime.fromisoformat(normalized).astimezone(tz=None)
    return dt_utc.strftime(_LOCAL_TIME_FORMAT)


def format_status_mark(status: AssignmentStatus) -> str:
    """Return a text mark for CLI display (not HTML)."""
    if status == AssignmentStatus.OK:
        return "ok"
    if status == AssignmentStatus.NAH:
        return "nah"
    return AssignmentStatus.PENDING.value


def _resolve_group_label(db: Database, group_id: int) -> str:
    for g in db.groups:
        if g.id == group_id:
            return format_group_ref(g)
    return f"g{group_id} (not found)"


def describe_project_state(state: ProjectState) -> str:
    return state.value
