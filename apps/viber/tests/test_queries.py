"""Tests for pending-assignment query functions."""

import pytest

from viber.models import AssignmentStatus, Database, ProjectState
from viber.queries import pending_all, pending_by_project, pending_by_task
from viber.service import (
    create_group,
    create_project,
    create_task,
    resolve_assignment,
    set_project_state,
)


def make_setup() -> tuple[Database, object, object, object, object, object]:
    """Create a db with 2 groups, 2 projects each, and 2 tasks."""
    db = Database()
    g1 = create_group(db, "Backend")
    g2 = create_group(db, "Frontend")
    p1 = create_project(db, "api", g1.id)
    p2 = create_project(db, "auth", g1.id)
    p3 = create_project(db, "ui", g2.id)
    t1 = create_task(db, "Update deps", None)   # all groups
    t2 = create_task(db, "Fix lint", g1.id)     # backend only
    return db, g1, g2, p1, p2, p3, t1, t2  # type: ignore[return-value]


def test_pending_all_returns_active_projects_only() -> None:
    db, g1, g2, p1, p2, p3, t1, t2 = make_setup()  # type: ignore[misc]
    entries = pending_all(db)  # type: ignore[arg-type]
    project_ids = {e.project.id for e in entries}
    assert p1.id in project_ids  # type: ignore[union-attr]
    assert p2.id in project_ids  # type: ignore[union-attr]
    assert p3.id in project_ids  # type: ignore[union-attr]


def test_pending_all_excludes_suspended() -> None:
    db, g1, g2, p1, p2, p3, t1, t2 = make_setup()  # type: ignore[misc]
    from viber.models import Project
    if isinstance(p1, Project):
        set_project_state(db, p1.id, ProjectState.SUSPENDED)  # type: ignore[arg-type]
    entries = pending_all(db)  # type: ignore[arg-type]
    project_ids = {e.project.id for e in entries}
    assert p1.id not in project_ids  # type: ignore[union-attr]


def test_pending_all_excludes_deprecated() -> None:
    db, g1, g2, p1, p2, p3, t1, t2 = make_setup()  # type: ignore[misc]
    from viber.models import Project
    if isinstance(p1, Project):
        set_project_state(db, p1.id, ProjectState.DEPRECATED)  # type: ignore[arg-type]
    entries = pending_all(db)  # type: ignore[arg-type]
    project_ids = {e.project.id for e in entries}
    assert p1.id not in project_ids  # type: ignore[union-attr]


def test_pending_all_empty_after_all_resolved() -> None:
    db = Database()
    g = create_group(db, "Backend")
    p = create_project(db, "api", g.id)
    t = create_task(db, "Task", None)
    resolve_assignment(db, p.id, t.id, AssignmentStatus.OK, None)
    entries = pending_all(db)
    assert entries == []


def test_pending_by_project_returns_pending_tasks() -> None:
    db = Database()
    g = create_group(db, "Backend")
    p = create_project(db, "api", g.id)
    t1 = create_task(db, "Task A", None)
    t2 = create_task(db, "Task B", None)
    resolve_assignment(db, p.id, t1.id, AssignmentStatus.OK, None)

    results = pending_by_project(db, p.id)
    task_ids = [r[0].id for r in results]
    assert t1.id not in task_ids
    assert t2.id in task_ids


def test_pending_by_project_returns_empty_for_suspended() -> None:
    db = Database()
    g = create_group(db, "Backend")
    p = create_project(db, "api", g.id)
    create_task(db, "Task", None)
    set_project_state(db, p.id, ProjectState.SUSPENDED)
    results = pending_by_project(db, p.id)
    assert results == []


def test_pending_by_project_not_found() -> None:
    db = Database()
    from viber.errors import ProjectNotFoundError
    with pytest.raises(ProjectNotFoundError):
        pending_by_project(db, 99)


def test_pending_by_task_returns_pending_projects() -> None:
    db = Database()
    g = create_group(db, "Backend")
    p1 = create_project(db, "api", g.id)
    p2 = create_project(db, "auth", g.id)
    t = create_task(db, "Task", None)
    resolve_assignment(db, p1.id, t.id, AssignmentStatus.OK, None)

    results = pending_by_task(db, t.id)
    project_ids = [r[0].id for r in results]
    assert p1.id not in project_ids
    assert p2.id in project_ids


def test_pending_by_task_excludes_suspended() -> None:
    db = Database()
    g = create_group(db, "Backend")
    p = create_project(db, "api", g.id)
    t = create_task(db, "Task", None)
    set_project_state(db, p.id, ProjectState.SUSPENDED)

    results = pending_by_task(db, t.id)
    assert results == []


def test_pending_by_task_not_found() -> None:
    db = Database()
    from viber.errors import TaskNotFoundError
    with pytest.raises(TaskNotFoundError):
        pending_by_task(db, 99)
