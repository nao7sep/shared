"""Tests for JSON persistence."""

import json
from pathlib import Path

from viber.models import (
    Assignment,
    AssignmentStatus,
    Database,
    Group,
    Project,
    ProjectState,
    Task,
)
from viber.store import load_database, save_database


def test_load_missing_file(tmp_path: Path) -> None:
    path = tmp_path / "data.json"
    db = load_database(path)
    assert isinstance(db, Database)
    assert db.groups == []


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "data.json"
    db = Database()
    db.groups.append(Group(id=1, name="Backend"))
    db.next_group_id = 2
    save_database(db, path)

    restored = load_database(path)
    assert len(restored.groups) == 1
    assert restored.groups[0].name == "Backend"
    assert restored.next_group_id == 2


def test_save_creates_parent_dirs(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "dir" / "data.json"
    db = Database()
    save_database(db, path)
    assert path.exists()


def test_save_trailing_newline(tmp_path: Path) -> None:
    path = tmp_path / "data.json"
    save_database(Database(), path)
    content = path.read_text(encoding="utf-8")
    assert content.endswith("\n")


def test_save_valid_json(tmp_path: Path) -> None:
    path = tmp_path / "data.json"
    db = Database()
    db.groups.append(Group(id=1, name="Test"))
    save_database(db, path)
    content = path.read_text(encoding="utf-8")
    parsed = json.loads(content)
    assert "groups" in parsed
    assert parsed["groups"][0]["name"] == "Test"


def test_save_uses_canonical_key_order(tmp_path: Path) -> None:
    path = tmp_path / "data.json"
    db = Database(
        next_group_id=2,
        next_project_id=11,
        next_task_id=4,
        groups=[Group(id=1, name="Backend")],
        projects=[
            Project(
                id=10,
                name="api",
                group_id=1,
                state=ProjectState.ACTIVE,
                created_utc="2026-03-01T00:00:00Z",
            )
        ],
        tasks=[
            Task(
                id=3,
                description="Release",
                group_id=None,
                created_utc="2026-03-02T00:00:00Z",
            )
        ],
        assignments={
            "10-3": Assignment(
                project_id=10,
                task_id=3,
                status=AssignmentStatus.PENDING,
                comment=None,
                handled_utc=None,
            )
        },
    )

    save_database(db, path)

    parsed = json.loads(path.read_text(encoding="utf-8"))
    assert list(parsed.keys()) == [
        "next_group_id",
        "next_project_id",
        "next_task_id",
        "groups",
        "projects",
        "tasks",
        "assignments",
    ]
    assert list(parsed["groups"][0].keys()) == ["id", "name"]
    assert list(parsed["projects"][0].keys()) == [
        "id",
        "name",
        "group_id",
        "state",
        "created_utc",
    ]
    assert list(parsed["tasks"][0].keys()) == [
        "id",
        "description",
        "group_id",
        "created_utc",
    ]
    assert list(parsed["assignments"]["10-3"].keys()) == [
        "project_id",
        "task_id",
        "status",
        "comment",
        "handled_utc",
    ]


def test_save_sorts_assignment_keys_numerically(tmp_path: Path) -> None:
    path = tmp_path / "data.json"
    db = Database(
        assignments={
            "10-2": Assignment(
                project_id=10,
                task_id=2,
                status=AssignmentStatus.PENDING,
                comment=None,
                handled_utc=None,
            ),
            "2-3": Assignment(
                project_id=2,
                task_id=3,
                status=AssignmentStatus.OK,
                comment="done",
                handled_utc="2026-03-01T00:00:00Z",
            ),
            "2-1": Assignment(
                project_id=2,
                task_id=1,
                status=AssignmentStatus.NAH,
                comment=None,
                handled_utc="2026-03-02T00:00:00Z",
            ),
        }
    )

    save_database(db, path)

    parsed = json.loads(path.read_text(encoding="utf-8"))
    assert list(parsed["assignments"].keys()) == ["2-1", "2-3", "10-2"]
