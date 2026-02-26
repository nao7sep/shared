"""Domain service layer: CRUD, lifecycle transitions, assignment generation."""

from __future__ import annotations

from datetime import UTC, datetime

from .errors import (
    AssignmentNotFoundError,
    DuplicateNameError,
    GroupInUseError,
    GroupNotFoundError,
    ProjectNotFoundError,
    TaskNotFoundError,
)
from .models import (
    Assignment,
    AssignmentStatus,
    Database,
    Group,
    Project,
    ProjectState,
    Task,
    assignment_key,
)

# ---------------------------------------------------------------------------
# Groups
# ---------------------------------------------------------------------------


def create_group(db: Database, name: str) -> Group:
    """Create a new group with case-insensitive unique name."""
    _check_group_name_unique(db, name, exclude_id=None)
    group = Group(id=db.next_group_id, name=name)
    db.next_group_id += 1
    db.groups.append(group)
    return group


def get_group(db: Database, group_id: int) -> Group:
    """Raise GroupNotFoundError if not found."""
    for g in db.groups:
        if g.id == group_id:
            return g
    raise GroupNotFoundError(group_id)


def list_groups(db: Database) -> list[Group]:
    return list(db.groups)


def update_group_name(db: Database, group_id: int, name: str) -> Group:
    """Rename a group with case-insensitive uniqueness enforced."""
    group = get_group(db, group_id)
    _check_group_name_unique(db, name, exclude_id=group_id)
    group.name = name
    return group


def delete_group(db: Database, group_id: int) -> Group:
    """Raise GroupInUseError if any project references this group."""
    group = get_group(db, group_id)
    for p in db.projects:
        if p.group_id == group_id:
            raise GroupInUseError(group_id)
    db.groups.remove(group)
    return group


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------


def create_project(db: Database, name: str, group_id: int) -> Project:
    """Create a new project in active state. No backfill of existing tasks."""
    get_group(db, group_id)  # validate group exists
    _check_project_name_unique(db, name, group_id, exclude_id=None)
    project = Project(
        id=db.next_project_id,
        name=name,
        group_id=group_id,
        state=ProjectState.ACTIVE,
        created_utc=_now_utc_iso_z(),
    )
    db.next_project_id += 1
    db.projects.append(project)
    return project


def get_project(db: Database, project_id: int) -> Project:
    """Raise ProjectNotFoundError if not found."""
    for p in db.projects:
        if p.id == project_id:
            return p
    raise ProjectNotFoundError(project_id)


def list_projects(db: Database) -> list[Project]:
    return list(db.projects)


def update_project_name(db: Database, project_id: int, name: str) -> Project:
    """Rename a project with uniqueness enforced within its group."""
    project = get_project(db, project_id)
    _check_project_name_unique(db, name, project.group_id, exclude_id=project_id)
    project.name = name
    return project


def set_project_state(db: Database, project_id: int, new_state: ProjectState) -> Project:
    """Transition project to any state. No assignment side effects."""
    project = get_project(db, project_id)
    project.state = new_state
    return project


def delete_project(db: Database, project_id: int) -> Project:
    """Cascade-delete all assignments for this project, then remove it."""
    project = get_project(db, project_id)
    keys_to_delete = [
        k for k, a in db.assignments.items() if a.project_id == project_id
    ]
    for k in keys_to_delete:
        del db.assignments[k]
    db.projects.remove(project)
    return project


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


def create_task(
    db: Database,
    description: str,
    group_id: int | None,
) -> Task:
    """Create a task and generate PENDING assignments for matching active projects.

    Assignments are generated only for projects that are:
    - state == ACTIVE
    - in the task's target group (or all groups if group_id is None)
    """
    if group_id is not None:
        get_group(db, group_id)  # validate group exists

    created_utc = _now_utc_iso_z()
    task = Task(
        id=db.next_task_id,
        description=description,
        created_utc=created_utc,
        group_id=group_id,
    )
    db.next_task_id += 1
    db.tasks.append(task)

    for project in db.projects:
        if project.state != ProjectState.ACTIVE:
            continue
        if group_id is not None and project.group_id != group_id:
            continue
        key = assignment_key(project.id, task.id)
        db.assignments[key] = Assignment(
            project_id=project.id,
            task_id=task.id,
            status=AssignmentStatus.PENDING,
            handled_utc=None,
        )

    return task


def get_task(db: Database, task_id: int) -> Task:
    """Raise TaskNotFoundError if not found."""
    for t in db.tasks:
        if t.id == task_id:
            return t
    raise TaskNotFoundError(task_id)


def list_tasks(db: Database) -> list[Task]:
    return list(db.tasks)


def update_task_description(db: Database, task_id: int, description: str) -> Task:
    """Update task description only; group_id is immutable."""
    task = get_task(db, task_id)
    task.description = description
    return task


def delete_task(db: Database, task_id: int) -> Task:
    """Cascade-delete all assignments for this task, then remove it."""
    task = get_task(db, task_id)
    keys_to_delete = [k for k, a in db.assignments.items() if a.task_id == task_id]
    for k in keys_to_delete:
        del db.assignments[k]
    db.tasks.remove(task)
    return task


# ---------------------------------------------------------------------------
# Assignments
# ---------------------------------------------------------------------------


def get_assignment(db: Database, project_id: int, task_id: int) -> Assignment:
    """Raise AssignmentNotFoundError if not found."""
    key = assignment_key(project_id, task_id)
    if key not in db.assignments:
        raise AssignmentNotFoundError(project_id, task_id)
    return db.assignments[key]


def resolve_assignment(
    db: Database,
    project_id: int,
    task_id: int,
    status: AssignmentStatus,
    comment: str | None,
) -> Assignment:
    """Validate entities exist, then update assignment status/comment/handled time."""
    get_project(db, project_id)
    get_task(db, task_id)
    assignment = get_assignment(db, project_id, task_id)
    assignment.status = status
    assignment.comment = comment
    assignment.handled_utc = _now_utc_iso_z() if status != AssignmentStatus.PENDING else None
    return assignment


def update_assignment_comment(
    db: Database,
    project_id: int,
    task_id: int,
    comment: str | None,
) -> Assignment:
    """Update assignment comment only."""
    get_project(db, project_id)
    get_task(db, task_id)
    assignment = get_assignment(db, project_id, task_id)
    assignment.comment = comment
    return assignment


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _check_group_name_unique(
    db: Database, name: str, exclude_id: int | None
) -> None:
    name_lower = name.lower()
    for g in db.groups:
        if g.id == exclude_id:
            continue
        if g.name.lower() == name_lower:
            raise DuplicateNameError(name)


def _check_project_name_unique(
    db: Database, name: str, group_id: int, exclude_id: int | None
) -> None:
    name_lower = name.lower()
    for p in db.projects:
        if p.group_id != group_id:
            continue
        if p.id == exclude_id:
            continue
        if p.name.lower() == name_lower:
            raise DuplicateNameError(name)


def _now_utc_iso_z() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
