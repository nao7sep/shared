"""Tests for domain models."""

from viber.models import (
    Assignment,
    AssignmentStatus,
    Database,
    Group,
    Project,
    ProjectState,
    Task,
    assignment_key,
)


def test_assignment_key_format() -> None:
    assert assignment_key(1, 2) == "1-2"
    assert assignment_key(10, 20) == "10-20"


def test_database_defaults() -> None:
    db = Database()
    assert db.next_group_id == 1
    assert db.next_project_id == 1
    assert db.next_task_id == 1
    assert db.groups == []
    assert db.projects == []
    assert db.tasks == []
    assert db.assignments == {}


def test_project_state_values() -> None:
    assert ProjectState.ACTIVE.value == "active"
    assert ProjectState.SUSPENDED.value == "suspended"
    assert ProjectState.DEPRECATED.value == "deprecated"


def test_assignment_status_values() -> None:
    assert AssignmentStatus.PENDING.value == "pending"
    assert AssignmentStatus.OK.value == "ok"
    assert AssignmentStatus.NAH.value == "nah"


def test_database_roundtrip() -> None:
    db = Database()
    db.groups.append(Group(id=1, name="Backend"))
    db.projects.append(
        Project(id=1, name="api", group_id=1, state=ProjectState.ACTIVE)
    )
    db.tasks.append(
        Task(
            id=1,
            description="Update deps",
            created_utc="2026-02-26T10:00:00.000000Z",
            group_id=None,
        )
    )
    db.assignments["1-1"] = Assignment(
        project_id=1, task_id=1, status=AssignmentStatus.PENDING
    )
    data = db.model_dump(mode="json")
    restored = Database.model_validate(data)
    assert restored.groups[0].name == "Backend"
    assert restored.projects[0].state == ProjectState.ACTIVE
    assert restored.assignments["1-1"].status == AssignmentStatus.PENDING
