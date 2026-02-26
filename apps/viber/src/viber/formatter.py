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

from .constants import (
    ASSIGNMENT_STATUS_NAH,
    ASSIGNMENT_STATUS_OK,
    LABEL_ALL_GROUPS,
    LABEL_GROUP_NOT_FOUND,
    LOCAL_TIME_FORMAT,
    UTC_OFFSET_ZERO,
    UTC_SUFFIX_Z,
)
from .models import Assignment, AssignmentStatus, Database, Group, Project, ProjectState, Task


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
        group_label = LABEL_ALL_GROUPS
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
    normalized = utc_iso.replace(UTC_SUFFIX_Z, UTC_OFFSET_ZERO)
    dt_utc = datetime.fromisoformat(normalized).astimezone(tz=None)
    return dt_utc.strftime(LOCAL_TIME_FORMAT)


def format_status_mark(status: AssignmentStatus) -> str:
    """Return a text mark for CLI display (not HTML)."""
    if status == AssignmentStatus.OK:
        return ASSIGNMENT_STATUS_OK
    if status == AssignmentStatus.NAH:
        return ASSIGNMENT_STATUS_NAH
    return AssignmentStatus.PENDING.value


def _resolve_group_label(db: Database, group_id: int) -> str:
    for g in db.groups:
        if g.id == group_id:
            return g.name
    return LABEL_GROUP_NOT_FOUND.format(group_id=group_id)


def describe_project_state(state: ProjectState) -> str:
    return state.value
