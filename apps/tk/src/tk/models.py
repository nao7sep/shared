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


_TASK_FIELDS = ("text", "status", "created_at", "handled_at", "subjective_date", "note")
_PROFILE_FIELDS = (
    "timezone",
    "subjective_day_start",
    "data_path",
    "output_path",
    "auto_sync",
    "sync_on_exit",
)
_VALID_TASK_STATUSES = {status.value for status in TaskStatus}


def _coerce_task_status(value: str) -> str:
    if value not in _VALID_TASK_STATUSES:
        raise ValueError(f"Invalid task status: {value}")
    return value


@dataclass
class Task:
    """In-memory task model."""

    text: str
    status: str
    created_at: str
    handled_at: str | None = None
    subjective_date: str | None = None
    note: str | None = None

    def __post_init__(self) -> None:
        self.status = _coerce_task_status(self.status)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Task":
        """Create task from a dict-like payload."""
        return cls(
            text=str(payload["text"]),
            status=str(payload["status"]),
            created_at=str(payload["created_at"]),
            handled_at=None if payload.get("handled_at") is None else str(payload.get("handled_at")),
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
            "created_at": self.created_at,
            "handled_at": self.handled_at,
            "subjective_date": self.subjective_date,
            "note": self.note,
        }

    # Dict-like interface kept for existing call sites.
    def __getitem__(self, key: str) -> Any:
        if key not in _TASK_FIELDS:
            raise KeyError(key)
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        if key not in _TASK_FIELDS:
            raise KeyError(key)

        if key == "status":
            self.status = _coerce_task_status(str(value))
            return

        if key in ("handled_at", "subjective_date", "note"):
            setattr(self, key, None if value is None else str(value))
            return

        setattr(self, key, str(value))

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def keys(self) -> tuple[str, ...]:
        return _TASK_FIELDS

    def __contains__(self, key: str) -> bool:
        return key in _TASK_FIELDS


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
                created_at=now_utc,
                handled_at=None,
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
        allowed_fields = {"text", "status", "handled_at", "subjective_date", "note"}
        invalid_fields = set(updates.keys()) - allowed_fields
        if invalid_fields:
            raise ValueError(f"Invalid task fields: {', '.join(sorted(invalid_fields))}")

        task = self.get_task_by_index(index)
        if task is None:
            return False

        for key, value in updates.items():
            task[key] = value
        return True

    def delete_task(self, index: int) -> bool:
        """Delete task at index."""
        if 0 <= index < len(self.tasks):
            self.tasks.pop(index)
            return True
        return False

    # Dict-like interface kept for existing call sites.
    def __getitem__(self, key: str) -> Any:
        if key != "tasks":
            raise KeyError(key)
        return self.tasks

    def __setitem__(self, key: str, value: Any) -> None:
        if key != "tasks":
            raise KeyError(key)
        if not isinstance(value, list):
            raise ValueError("Invalid tasks file structure: 'tasks' must be an array")
        self.tasks = [
            task if isinstance(task, Task) else Task.from_dict(task)
            for task in value
        ]

    def get(self, key: str, default: Any = None) -> Any:
        if key == "tasks":
            return self.tasks
        return default

    def keys(self) -> tuple[str, ...]:
        return ("tasks",)

    def __contains__(self, key: str) -> bool:
        return key == "tasks"


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
        return cls(
            timezone=str(payload["timezone"]),
            subjective_day_start=str(payload["subjective_day_start"]),
            data_path=str(payload["data_path"]),
            output_path=str(payload["output_path"]),
            auto_sync=bool(payload.get("auto_sync", True)),
            sync_on_exit=bool(payload.get("sync_on_exit", False)),
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

    # Dict-like interface kept for existing call sites.
    def __getitem__(self, key: str) -> Any:
        if key not in _PROFILE_FIELDS:
            raise KeyError(key)
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        if key not in _PROFILE_FIELDS:
            raise KeyError(key)
        if key in ("auto_sync", "sync_on_exit"):
            setattr(self, key, bool(value))
        else:
            setattr(self, key, str(value))

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def keys(self) -> tuple[str, ...]:
        return _PROFILE_FIELDS

    def __contains__(self, key: str) -> bool:
        return key in _PROFILE_FIELDS


@dataclass
class TaskListItem:
    """Display mapping for list/history output rows."""

    display_num: int
    array_index: int
    task: Task

    def __getitem__(self, key: str) -> Any:
        if key == "display_num":
            return self.display_num
        if key == "array_index":
            return self.array_index
        if key == "task":
            return self.task
        raise KeyError(key)

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default


@dataclass
class PendingListPayload:
    """Pending-list payload for presenters."""

    items: list[TaskListItem] = field(default_factory=list)

    def __getitem__(self, key: str) -> Any:
        if key == "items":
            return self.items
        raise KeyError(key)

    def get(self, key: str, default: Any = None) -> Any:
        if key == "items":
            return self.items
        return default

    def __contains__(self, key: str) -> bool:
        return key == "items"


@dataclass
class HistoryFilters:
    """Selected history filters used to produce payload."""

    days: int | None = None
    working_days: int | None = None
    specific_date: str | None = None

    def __getitem__(self, key: str) -> Any:
        if key == "days":
            return self.days
        if key == "working_days":
            return self.working_days
        if key == "specific_date":
            return self.specific_date
        raise KeyError(key)

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default


@dataclass
class HistoryGroup:
    """Date-grouped handled tasks for presenter output."""

    date: str
    items: list[TaskListItem] = field(default_factory=list)

    def __getitem__(self, key: str) -> Any:
        if key == "date":
            return self.date
        if key == "items":
            return self.items
        raise KeyError(key)

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default


@dataclass
class HistoryListPayload:
    """History payload for presenters."""

    groups: list[HistoryGroup] = field(default_factory=list)
    filters: HistoryFilters = field(default_factory=HistoryFilters)

    def __getitem__(self, key: str) -> Any:
        if key == "groups":
            return self.groups
        if key == "filters":
            return self.filters
        raise KeyError(key)

    def get(self, key: str, default: Any = None) -> Any:
        if key == "groups":
            return self.groups
        if key == "filters":
            return self.filters
        return default

    def __contains__(self, key: str) -> bool:
        return key in ("groups", "filters")
