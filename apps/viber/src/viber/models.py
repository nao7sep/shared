"""Domain models for viber."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class ProjectState(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEPRECATED = "deprecated"


class AssignmentStatus(StrEnum):
    PENDING = "pending"
    OK = "ok"
    NAH = "nah"


class Group(BaseModel):
    id: int
    name: str


class Project(BaseModel):
    id: int
    name: str
    group_id: int
    state: ProjectState


class Task(BaseModel):
    id: int
    description: str
    created_utc: str  # ISO 8601 with 'Z' suffix, high precision
    group_id: int | None  # None = applies to all groups


class Assignment(BaseModel):
    project_id: int
    task_id: int
    status: AssignmentStatus
    comment: str | None = None


class Database(BaseModel):
    next_group_id: int = 1
    next_project_id: int = 1
    next_task_id: int = 1
    groups: list[Group] = []
    projects: list[Project] = []
    tasks: list[Task] = []
    # Keyed by composite "project_id-task_id" for O(1) lookup
    assignments: dict[str, Assignment] = {}


def assignment_key(project_id: int, task_id: int) -> str:
    """Return the composite key used to look up an assignment."""
    return f"{project_id}-{task_id}"
