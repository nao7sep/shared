"""CLI output formatting helpers.

Follows the shared CLI output formatting standards spec:
- One blank line between semantic segments (leading-blank strategy).
- Explicit empty-state feedback.
- No colors or text decorations.
- No hard-wrapping.
"""

from __future__ import annotations

from datetime import datetime

from .models import Database, Group, Project, Task

_LOCAL_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


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


def format_local_time(utc_iso: str) -> str:
    """Parse UTC ISO string, convert to local time, format as 'YYYY-MM-DD HH:MM:SS'."""
    # Handle both '+00:00' and 'Z' suffixes
    normalized = utc_iso.replace("Z", "+00:00")
    dt_utc = datetime.fromisoformat(normalized).astimezone(tz=None)
    return dt_utc.strftime(_LOCAL_TIME_FORMAT)


def _resolve_group_label(db: Database, group_id: int) -> str:
    for g in db.groups:
        if g.id == group_id:
            return format_group_ref(g)
    return f"g{group_id} (not found)"
