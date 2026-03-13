"""Tests for domain service layer."""

import pytest

from viber.errors import (
    AssignmentNotFoundError,
    DuplicateNameError,
    GroupNotFoundError,
    ProjectNotFoundError,
    TaskNotFoundError,
)
from viber.models import AssignmentStatus, Database, ProjectState, assignment_key
from viber.service import (
    create_group,
    create_project,
    create_task,
    delete_group,
    delete_project,
    delete_task,
    ensure_active_project_assignments,
    get_assignment,
    get_group,
    get_project,
    get_task,
    repair_active_project_assignments,
    resolve_assignment,
    set_project_state,
    undo_assignment,
    update_assignment_comment,
    update_group_name,
    update_project_name,
    update_task_description,
)


def make_db() -> Database:
    return Database()


# ---------------------------------------------------------------------------
# Groups
# ---------------------------------------------------------------------------


def test_create_group() -> None:
    db = make_db()
    g = create_group(db, "Backend")
    assert g.id == 1
    assert g.name == "Backend"
    assert db.next_group_id == 2
    assert len(db.groups) == 1


def test_create_group_id_increments() -> None:
    db = make_db()
    g1 = create_group(db, "A")
    g2 = create_group(db, "B")
    assert g1.id == 1
    assert g2.id == 2


def test_create_group_duplicate_raises() -> None:
    db = make_db()
    create_group(db, "Backend")
    with pytest.raises(DuplicateNameError):
        create_group(db, "Backend")


def test_create_group_case_insensitive_duplicate() -> None:
    db = make_db()
    create_group(db, "Backend")
    with pytest.raises(DuplicateNameError):
        create_group(db, "backend")


def test_get_group_not_found() -> None:
    db = make_db()
    with pytest.raises(GroupNotFoundError):
        get_group(db, 99)


def test_delete_group_cascades_projects_tasks_and_assignments() -> None:
    db = make_db()
    g1 = create_group(db, "Backend")
    g2 = create_group(db, "Frontend")
    p1 = create_project(db, "api", g1.id)
    p2 = create_project(db, "ui", g2.id)

    # all groups task; assignments for p1 and p2
    t_all = create_task(db, "Shared task", None)
    # group-scoped task in g1; assignment for p1 only
    t_g1 = create_task(db, "Backend task", g1.id)
    # group-scoped task in g2; assignment for p2 only
    t_g2 = create_task(db, "Frontend task", g2.id)

    key_p1_tall = assignment_key(p1.id, t_all.id)
    key_p2_tall = assignment_key(p2.id, t_all.id)
    key_p1_tg1 = assignment_key(p1.id, t_g1.id)
    key_p2_tg2 = assignment_key(p2.id, t_g2.id)
    assert key_p1_tall in db.assignments
    assert key_p2_tall in db.assignments
    assert key_p1_tg1 in db.assignments
    assert key_p2_tg2 in db.assignments

    delete_group(db, g1.id)

    # group and its projects are deleted
    assert all(g.id != g1.id for g in db.groups)
    assert all(p.group_id != g1.id for p in db.projects)

    # tasks scoped to deleted group are deleted; all-group and other-group tasks remain
    remaining_task_ids = {t.id for t in db.tasks}
    assert t_g1.id not in remaining_task_ids
    assert t_all.id in remaining_task_ids
    assert t_g2.id in remaining_task_ids

    # assignments tied to deleted project/task are removed; unrelated remain
    assert key_p1_tall not in db.assignments
    assert key_p1_tg1 not in db.assignments
    assert key_p2_tall in db.assignments
    assert key_p2_tg2 in db.assignments


def test_delete_group_success() -> None:
    db = make_db()
    g = create_group(db, "Backend")
    deleted = delete_group(db, g.id)
    assert deleted.id == g.id
    assert db.groups == []


def test_delete_group_keeps_orphan_all_group_tasks() -> None:
    db = make_db()
    g = create_group(db, "Backend")
    create_project(db, "api", g.id)
    t = create_task(db, "Shared task", None)
    assert any(task.id == t.id for task in db.tasks)

    delete_group(db, g.id)

    assert db.groups == []
    assert db.projects == []
    assert db.tasks == [t]
    assert db.assignments == {}


def test_update_group_name() -> None:
    db = make_db()
    g = create_group(db, "Backend")
    updated = update_group_name(db, g.id, "Platform")
    assert updated.name == "Platform"


def test_update_group_name_duplicate_raises() -> None:
    db = make_db()
    g1 = create_group(db, "Backend")
    create_group(db, "Frontend")
    with pytest.raises(DuplicateNameError):
        update_group_name(db, g1.id, "frontend")


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------


def test_create_project() -> None:
    db = make_db()
    g = create_group(db, "Backend")
    p = create_project(db, "api-server", g.id)
    assert p.id == 1
    assert p.name == "api-server"
    assert p.group_id == g.id
    assert p.state == ProjectState.ACTIVE
    assert p.created_utc is not None
    assert p.created_utc.endswith("Z")


def test_create_project_group_not_found() -> None:
    db = make_db()
    with pytest.raises(GroupNotFoundError):
        create_project(db, "api", 99)


def test_create_project_duplicate_name_in_group() -> None:
    db = make_db()
    g = create_group(db, "Backend")
    create_project(db, "api", g.id)
    with pytest.raises(DuplicateNameError):
        create_project(db, "API", g.id)


def test_create_project_same_name_different_group_allowed() -> None:
    db = make_db()
    g1 = create_group(db, "Backend")
    g2 = create_group(db, "Frontend")
    create_project(db, "web", g1.id)
    p2 = create_project(db, "web", g2.id)
    assert p2.group_id == g2.id


def test_create_project_backfills_existing_applicable_tasks() -> None:
    db = make_db()
    g1 = create_group(db, "Backend")
    g2 = create_group(db, "Frontend")
    t_all = create_task(db, "All task", None)
    t_g1 = create_task(db, "Backend task", g1.id)
    t_g2 = create_task(db, "Frontend task", g2.id)

    p = create_project(db, "api", g1.id)

    assert assignment_key(p.id, t_all.id) in db.assignments
    assert assignment_key(p.id, t_g1.id) in db.assignments
    assert assignment_key(p.id, t_g2.id) not in db.assignments


def test_create_project_backfills_as_pending() -> None:
    db = make_db()
    g = create_group(db, "Backend")
    t = create_task(db, "Task 1", None)
    p = create_project(db, "api", g.id)
    assignment = db.assignments[assignment_key(p.id, t.id)]

    assert assignment.status == AssignmentStatus.PENDING
    assert assignment.comment is None
    assert assignment.handled_utc is None


def test_set_project_state() -> None:
    db = make_db()
    g = create_group(db, "Backend")
    p = create_project(db, "api", g.id)
    updated = set_project_state(db, p.id, ProjectState.SUSPENDED)
    assert updated.state == ProjectState.SUSPENDED


def test_update_project_name() -> None:
    db = make_db()
    g = create_group(db, "Backend")
    p = create_project(db, "api", g.id)
    updated = update_project_name(db, p.id, "service-api")
    assert updated.name == "service-api"


def test_update_project_name_duplicate_raises() -> None:
    db = make_db()
    g = create_group(db, "Backend")
    p1 = create_project(db, "api", g.id)
    create_project(db, "auth", g.id)
    with pytest.raises(DuplicateNameError):
        update_project_name(db, p1.id, "AUTH")


def test_delete_project_cascades_assignments() -> None:
    db = make_db()
    g = create_group(db, "Backend")
    p = create_project(db, "api", g.id)
    t = create_task(db, "Task 1", None)
    key = assignment_key(p.id, t.id)
    assert key in db.assignments

    delete_project(db, p.id)
    assert key not in db.assignments
    assert db.projects == []


def test_delete_project_keeps_tasks_without_assignments() -> None:
    db = make_db()
    g = create_group(db, "Backend")
    p = create_project(db, "api", g.id)
    t = create_task(db, "Task 1", None)
    assert any(task.id == t.id for task in db.tasks)

    delete_project(db, p.id)

    assert db.projects == []
    assert db.tasks == [t]
    assert db.assignments == {}


def test_get_project_not_found() -> None:
    db = make_db()
    with pytest.raises(ProjectNotFoundError):
        get_project(db, 99)


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


def test_create_task_generates_assignments_for_active_projects() -> None:
    db = make_db()
    g = create_group(db, "Backend")
    p1 = create_project(db, "api", g.id)
    p2 = create_project(db, "auth", g.id)

    t = create_task(db, "Update deps", None)

    assert assignment_key(p1.id, t.id) in db.assignments
    assert assignment_key(p2.id, t.id) in db.assignments
    assert db.assignments[assignment_key(p1.id, t.id)].status == AssignmentStatus.PENDING
    assert db.assignments[assignment_key(p1.id, t.id)].handled_utc is None


def test_create_task_skips_suspended_project() -> None:
    db = make_db()
    g = create_group(db, "Backend")
    p = create_project(db, "api", g.id)
    set_project_state(db, p.id, ProjectState.SUSPENDED)

    t = create_task(db, "Task", None)
    assert assignment_key(p.id, t.id) not in db.assignments


def test_create_task_skips_deprecated_project() -> None:
    db = make_db()
    g = create_group(db, "Backend")
    p = create_project(db, "api", g.id)
    set_project_state(db, p.id, ProjectState.DEPRECATED)

    t = create_task(db, "Task", None)
    assert assignment_key(p.id, t.id) not in db.assignments


def test_create_task_with_target_group_skips_other_groups() -> None:
    db = make_db()
    g1 = create_group(db, "Backend")
    g2 = create_group(db, "Frontend")
    p1 = create_project(db, "api", g1.id)
    p2 = create_project(db, "ui", g2.id)

    t = create_task(db, "Backend task", g1.id)

    assert assignment_key(p1.id, t.id) in db.assignments
    assert assignment_key(p2.id, t.id) not in db.assignments


def test_create_task_group_not_found() -> None:
    db = make_db()
    from viber.errors import GroupNotFoundError
    with pytest.raises(GroupNotFoundError):
        create_task(db, "Task", 99)


def test_update_task_description() -> None:
    db = make_db()
    g = create_group(db, "Backend")
    create_project(db, "api", g.id)
    t = create_task(db, "Old desc", None)
    updated = update_task_description(db, t.id, "New desc")
    assert updated.description == "New desc"


def test_delete_task_cascades_assignments() -> None:
    db = make_db()
    g = create_group(db, "Backend")
    p = create_project(db, "api", g.id)
    t = create_task(db, "Task", None)
    key = assignment_key(p.id, t.id)
    assert key in db.assignments

    delete_task(db, t.id)
    assert key not in db.assignments
    assert db.tasks == []


def test_get_task_not_found() -> None:
    db = make_db()
    with pytest.raises(TaskNotFoundError):
        get_task(db, 99)


# ---------------------------------------------------------------------------
# Assignments
# ---------------------------------------------------------------------------


def test_resolve_assignment_ok() -> None:
    db = make_db()
    g = create_group(db, "Backend")
    p = create_project(db, "api", g.id)
    t = create_task(db, "Task", None)

    a = resolve_assignment(db, p.id, t.id, AssignmentStatus.OK, "Done")
    assert a.status == AssignmentStatus.OK
    assert a.comment == "Done"
    assert a.handled_utc is not None
    assert a.handled_utc.endswith("Z")


def test_resolve_assignment_nah() -> None:
    db = make_db()
    g = create_group(db, "Backend")
    p = create_project(db, "api", g.id)
    t = create_task(db, "Task", None)

    a = resolve_assignment(db, p.id, t.id, AssignmentStatus.NAH, None)
    assert a.status == AssignmentStatus.NAH
    assert a.comment is None
    assert a.handled_utc is not None
    assert a.handled_utc.endswith("Z")


def test_resolve_assignment_pending_clears_handled_timestamp() -> None:
    db = make_db()
    g = create_group(db, "Backend")
    p = create_project(db, "api", g.id)
    t = create_task(db, "Task", None)

    a = resolve_assignment(db, p.id, t.id, AssignmentStatus.OK, None)
    assert a.handled_utc is not None

    a = resolve_assignment(db, p.id, t.id, AssignmentStatus.PENDING, None)
    assert a.status == AssignmentStatus.PENDING
    assert a.handled_utc is None


def test_update_assignment_comment_set_and_clear() -> None:
    db = make_db()
    g = create_group(db, "Backend")
    p = create_project(db, "api", g.id)
    t = create_task(db, "Task", None)

    updated = update_assignment_comment(db, p.id, t.id, "Need follow-up")
    assert updated.comment == "Need follow-up"

    cleared = update_assignment_comment(db, p.id, t.id, None)
    assert cleared.comment is None


def test_get_assignment_not_found() -> None:
    db = make_db()
    g = create_group(db, "Backend")
    create_project(db, "api", g.id)
    create_task(db, "Task", None)
    with pytest.raises(AssignmentNotFoundError):
        get_assignment(db, 999, 1)


def test_reactivating_suspended_project_backfills_missing_tasks() -> None:
    db = make_db()
    g = create_group(db, "Backend")
    p = create_project(db, "api", g.id)
    set_project_state(db, p.id, ProjectState.SUSPENDED)
    t1 = create_task(db, "Task during suspension", None)
    assert assignment_key(p.id, t1.id) not in db.assignments

    set_project_state(db, p.id, ProjectState.ACTIVE)
    assert assignment_key(p.id, t1.id) in db.assignments

    t2 = create_task(db, "Task after reactivation", None)
    assert assignment_key(p.id, t2.id) in db.assignments


def test_reactivating_deprecated_project_backfills_missing_tasks() -> None:
    db = make_db()
    g = create_group(db, "Backend")
    p = create_project(db, "api", g.id)
    set_project_state(db, p.id, ProjectState.DEPRECATED)

    t = create_task(db, "Task during deprecation", None)
    assert assignment_key(p.id, t.id) not in db.assignments

    set_project_state(db, p.id, ProjectState.ACTIVE)
    assert assignment_key(p.id, t.id) in db.assignments


def test_ensure_active_project_assignments_is_idempotent() -> None:
    db = make_db()
    g = create_group(db, "Backend")
    p = create_project(db, "api", g.id)
    t = create_task(db, "Task", None)
    key = assignment_key(p.id, t.id)

    del db.assignments[key]

    created = ensure_active_project_assignments(db, p.id)
    created_again = ensure_active_project_assignments(db, p.id)

    assert [assignment.task_id for assignment in created] == [t.id]
    assert created_again == []
    assert key in db.assignments


def test_repair_active_project_assignments_only_repairs_active_projects() -> None:
    db = make_db()
    g = create_group(db, "Backend")
    active = create_project(db, "api", g.id)
    inactive = create_project(db, "worker", g.id)
    t = create_task(db, "Task", None)
    active_key = assignment_key(active.id, t.id)
    inactive_key = assignment_key(inactive.id, t.id)

    set_project_state(db, inactive.id, ProjectState.SUSPENDED)
    del db.assignments[active_key]
    del db.assignments[inactive_key]

    created = repair_active_project_assignments(db)

    assert [assignment.project_id for assignment in created] == [active.id]
    assert active_key in db.assignments
    assert inactive_key not in db.assignments


# ---------------------------------------------------------------------------
# Undo assignment
# ---------------------------------------------------------------------------


def test_undo_assignment_resets_to_pending() -> None:
    db = make_db()
    g = create_group(db, "Backend")
    p = create_project(db, "api", g.id)
    t = create_task(db, "Task", None)

    resolve_assignment(db, p.id, t.id, AssignmentStatus.OK, "Done")
    a = undo_assignment(db, p.id, t.id)

    assert a.status == AssignmentStatus.PENDING
    assert a.comment is None
    assert a.handled_utc is None


def test_undo_assignment_clears_nah_with_comment() -> None:
    db = make_db()
    g = create_group(db, "Backend")
    p = create_project(db, "api", g.id)
    t = create_task(db, "Task", None)

    resolve_assignment(db, p.id, t.id, AssignmentStatus.NAH, "Not applicable")
    a = undo_assignment(db, p.id, t.id)

    assert a.status == AssignmentStatus.PENDING
    assert a.comment is None
    assert a.handled_utc is None


def test_undo_assignment_not_found() -> None:
    db = make_db()
    g1 = create_group(db, "Backend")
    g2 = create_group(db, "Frontend")
    create_project(db, "api", g1.id)
    p2 = create_project(db, "ui", g2.id)
    t = create_task(db, "Backend task", g1.id)
    with pytest.raises(AssignmentNotFoundError):
        undo_assignment(db, p2.id, t.id)
