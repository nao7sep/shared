"""Typed domain models and payload DTOs for tk."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping


class TaskStatus(str, Enum):
    """Task lifecycle statuses."""

    PENDING = "pending"
    DONE = "done"
    CANCELLED = "cancelled"


_VALID_TASK_STATUSES = {status.value for status in TaskStatus}


def _coerce_task_status(value: str) -> str:
    if isinstance(value, TaskStatus):
        return value.value
    if value not in _VALID_TASK_STATUSES:
        raise ValueError(f"Invalid task status: {value}")
    return value


@dataclass
class Task:
    """In-memory task model."""

    text: str
    status: str
    created_utc: str
    handled_utc: str | None = None
    subjective_date: str | None = None
    note: str | None = None

    def __post_init__(self) -> None:
        self.status = _coerce_task_status(self.status)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Task":
        """Create task from a dict-like payload."""
        required_fields = {"text", "status", "created_utc"}
        missing = required_fields - set(payload.keys())
        if missing:
            raise ValueError(f"Task missing required fields: {', '.join(sorted(missing))}")

        created_utc = payload["created_utc"]
        if created_utc is None:
            raise ValueError("Task missing required field: created_utc")

        handled_utc = payload.get("handled_utc")

        return cls(
            text=str(payload["text"]),
            status=str(payload["status"]),
            created_utc=str(created_utc),
            handled_utc=None if handled_utc is None else str(handled_utc),
            subjective_date=None
            if payload.get("subjective_date") is None
            else str(payload.get("subjective_date")),
            note=None if payload.get("note") is None else str(payload.get("note")),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize task to dict payload."""
        return {
            "text": self.text,
            "status": self.status,
            "created_utc": self.created_utc,
            "handled_utc": self.handled_utc,
            "subjective_date": self.subjective_date,
            "note": self.note,
        }


@dataclass
class TaskStore:
    """Collection model for task persistence payload."""

    tasks: list[Task] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TaskStore":
        """Create task store from dict payload."""
        raw_tasks = payload.get("tasks")
        if raw_tasks is None:
            raise ValueError("Invalid tasks file structure: missing 'tasks' key")
        if not isinstance(raw_tasks, list):
            raise ValueError("Invalid tasks file structure: 'tasks' must be an array")

        tasks: list[Task] = []
        for i, raw_task in enumerate(raw_tasks):
            if isinstance(raw_task, Task):
                tasks.append(raw_task)
                continue
            if not isinstance(raw_task, Mapping):
                raise ValueError(f"Task {i} is not a valid object")
            tasks.append(Task.from_dict(raw_task))

        return cls(tasks=tasks)

    def to_dict(self) -> dict[str, Any]:
        """Serialize store to persistence dict payload."""
        return {"tasks": [task.to_dict() for task in self.tasks]}

    def add_task(self, text: str) -> int:
        """Append a new pending task and return its array index."""
        now_utc = datetime.now(timezone.utc).isoformat()
        self.tasks.append(
            Task(
                text=text,
                status=TaskStatus.PENDING.value,
                created_utc=now_utc,
                handled_utc=None,
                subjective_date=None,
                note=None,
            )
        )
        return len(self.tasks) - 1

    def get_task_by_index(self, index: int) -> Task | None:
        """Return task by array index."""
        if 0 <= index < len(self.tasks):
            return self.tasks[index]
        return None

    def update_task(self, index: int, **updates: Any) -> bool:
        """Update task fields at index."""
        allowed_fields = {"text", "status", "handled_utc", "subjective_date", "note"}
        invalid_fields = set(updates.keys()) - allowed_fields
        if invalid_fields:
            raise ValueError(f"Invalid task fields: {', '.join(sorted(invalid_fields))}")

        task = self.get_task_by_index(index)
        if task is None:
            return False

        for key, value in updates.items():
            if key == "status":
                task.status = _coerce_task_status(value)
            elif key in ("handled_utc", "subjective_date", "note"):
                setattr(task, key, None if value is None else str(value))
            else:
                setattr(task, key, str(value))
        return True

    def delete_task(self, index: int) -> bool:
        """Delete task at index."""
        if 0 <= index < len(self.tasks):
            self.tasks.pop(index)
            return True
        return False


@dataclass
class Profile:
    """In-memory profile model."""

    timezone: str
    subjective_day_start: str
    data_path: str
    output_path: str
    auto_sync: bool = True
    sync_on_exit: bool = False

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Profile":
        """Create profile model from dict payload."""
        auto_sync = payload.get("auto_sync", True)
        sync_on_exit = payload.get("sync_on_exit", False)
        return cls(
            timezone=str(payload["timezone"]),
            subjective_day_start=str(payload["subjective_day_start"]),
            data_path=str(payload["data_path"]),
            output_path=str(payload["output_path"]),
            auto_sync=auto_sync,
            sync_on_exit=sync_on_exit,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize profile model to dict payload."""
        return {
            "timezone": self.timezone,
            "subjective_day_start": self.subjective_day_start,
            "data_path": self.data_path,
            "output_path": self.output_path,
            "auto_sync": self.auto_sync,
            "sync_on_exit": self.sync_on_exit,
        }


@dataclass
class TaskListItem:
    """Display mapping for list/history output rows."""

    display_num: int
    array_index: int
    task: Task


@dataclass
class PendingListPayload:
    """Pending-list payload for presenters."""

    items: list[TaskListItem] = field(default_factory=list)


@dataclass
class HistoryFilters:
    """Selected history filters used to produce payload."""

    days: int | None = None
    working_days: int | None = None
    specific_date: str | None = None


@dataclass
class HistoryGroup:
    """Date-grouped handled tasks for presenter output."""

    date: str
    items: list[TaskListItem] = field(default_factory=list)


@dataclass
class HistoryListPayload:
    """History payload for presenters."""

    groups: list[HistoryGroup] = field(default_factory=list)
    filters: HistoryFilters = field(default_factory=HistoryFilters)


@dataclass
class GroupedTaskDisplay:
    """Tasks grouped by status for TODO/markdown display."""

    pending: list[Task] = field(default_factory=list)
    done: list[tuple[str, list[Task]]] = field(default_factory=list)
    cancelled: list[tuple[str, list[Task]]] = field(default_factory=list)


@dataclass
class DoneCancelResult:
    """Result of interactive done/cancel prompts."""

    note: str | None
    date: str


@dataclass
class CommandDocEntry:
    """Metadata for a single command in the help/doc system."""

    command: str
    alias: str
    usage: str
    summary: str
    display_usage: str
