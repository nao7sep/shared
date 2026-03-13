"""JSON state file persistence."""

from __future__ import annotations

import json
from pathlib import Path

from .models import Assignment, Database, Group, Project, Task


def load_database(path: Path) -> Database:
    """Load database from JSON file. Returns an empty Database if file does not exist."""
    if not path.exists():
        return Database()
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    return Database.model_validate(data)


def save_database(db: Database, path: Path) -> None:
    """Serialize database to JSON and write to path.

    Uses indent=2 and explicit canonical key ordering.
    Creates parent directories if needed.
    Appends a trailing newline.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _serialize_database(db)
    text = json.dumps(data, indent=2, ensure_ascii=False)
    path.write_text(text + "\n", encoding="utf-8")


def _serialize_database(db: Database) -> dict[str, object]:
    assignments = {
        key: _serialize_assignment(db.assignments[key])
        for key in sorted(db.assignments, key=_assignment_sort_key)
    }
    return {
        "next_group_id": db.next_group_id,
        "next_project_id": db.next_project_id,
        "next_task_id": db.next_task_id,
        "groups": [_serialize_group(group) for group in db.groups],
        "projects": [_serialize_project(project) for project in db.projects],
        "tasks": [_serialize_task(task) for task in db.tasks],
        "assignments": assignments,
    }


def _serialize_group(group: Group) -> dict[str, object]:
    return {
        "id": group.id,
        "name": group.name,
    }


def _serialize_project(project: Project) -> dict[str, object]:
    return {
        "id": project.id,
        "name": project.name,
        "group_id": project.group_id,
        "state": project.state.value,
        "created_utc": project.created_utc,
    }


def _serialize_task(task: Task) -> dict[str, object]:
    return {
        "id": task.id,
        "description": task.description,
        "group_id": task.group_id,
        "created_utc": task.created_utc,
    }


def _serialize_assignment(assignment: Assignment) -> dict[str, object]:
    return {
        "project_id": assignment.project_id,
        "task_id": assignment.task_id,
        "status": assignment.status.value,
        "comment": assignment.comment,
        "handled_utc": assignment.handled_utc,
    }


def _assignment_sort_key(key: str) -> tuple[int, int]:
    project_id_str, task_id_str = key.split("-", maxsplit=1)
    return int(project_id_str), int(task_id_str)
