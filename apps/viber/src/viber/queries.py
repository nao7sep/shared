"""Pending-assignment query layer."""

from __future__ import annotations

from dataclasses import dataclass

from .constants import ASSIGNMENT_STATUS_PENDING
from .errors import ProjectNotFoundError, TaskNotFoundError
from .models import Assignment, Database, Group, Project, ProjectState, Task, assignment_key


@dataclass
class PendingEntry:
    project: Project
    group: Group
    task: Task
    assignment: Assignment


def pending_all(db: Database) -> list[PendingEntry]:
    """Return all pending assignments, excluding SUSPENDED and DEPRECATED projects.

    Ordered by: group name asc, project name asc, task created_utc asc.
    """
    group_map = {g.id: g for g in db.groups}

    results: list[PendingEntry] = []
    for project in db.projects:
        if project.state != ProjectState.ACTIVE:
            continue
        group = group_map.get(project.group_id)
        if group is None:
            continue
        for task in db.tasks:
            key = assignment_key(project.id, task.id)
            a = db.assignments.get(key)
            if a is None or a.status.value != ASSIGNMENT_STATUS_PENDING:
                continue
            results.append(PendingEntry(project=project, group=group, task=task, assignment=a))

    results.sort(
        key=lambda e: (
            e.group.name.lower(),
            e.project.name.lower(),
            e.task.created_utc,
        )
    )
    return results


def pending_by_project(db: Database, project_id: int) -> list[tuple[Task, Assignment]]:
    """Return pending tasks for one project, ordered by task created_utc asc.

    Raises ProjectNotFoundError if project not found.
    Returns empty list if project is SUSPENDED or DEPRECATED (view excludes them).
    """
    project = _find_project(db, project_id)
    if project is None:
        raise ProjectNotFoundError(project_id)
    if project.state != ProjectState.ACTIVE:
        return []

    results: list[tuple[Task, Assignment]] = []
    for task in db.tasks:
        key = assignment_key(project_id, task.id)
        a = db.assignments.get(key)
        if a is None or a.status.value != ASSIGNMENT_STATUS_PENDING:
            continue
        results.append((task, a))

    results.sort(key=lambda x: x[0].created_utc)
    return results


def pending_by_task(
    db: Database, task_id: int
) -> list[tuple[Project, Group, Assignment]]:
    """Return pending projects for one task, excluding SUSPENDED/DEPRECATED.

    Ordered by group name asc, project name asc.
    Raises TaskNotFoundError if task not found.
    """
    task = _find_task(db, task_id)
    if task is None:
        raise TaskNotFoundError(task_id)

    group_map = {g.id: g for g in db.groups}
    results: list[tuple[Project, Group, Assignment]] = []

    for project in db.projects:
        if project.state != ProjectState.ACTIVE:
            continue
        group = group_map.get(project.group_id)
        if group is None:
            continue
        key = assignment_key(project.id, task_id)
        a = db.assignments.get(key)
        if a is None or a.status.value != ASSIGNMENT_STATUS_PENDING:
            continue
        results.append((project, group, a))

    results.sort(key=lambda x: (x[1].name.lower(), x[0].name.lower()))
    return results


def _find_project(db: Database, project_id: int) -> Project | None:
    for p in db.projects:
        if p.id == project_id:
            return p
    return None


def _find_task(db: Database, task_id: int) -> Task | None:
    for t in db.tasks:
        if t.id == task_id:
            return t
    return None
