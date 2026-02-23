"""Session state container for tk runtime."""

from dataclasses import dataclass, field
from typing import Any

from tk.models import Profile, Task, TaskStore


@dataclass
class Session:
    """In-memory runtime state for a tk session."""

    profile_path: str | None = None
    profile: Profile | dict[str, Any] | None = None
    tasks: TaskStore | dict[str, Any] | None = None
    last_list: list[tuple[int, int]] = field(default_factory=list)

    def require_profile(self) -> Profile:
        """Return loaded profile or raise if missing."""
        if self.profile is None:
            raise ValueError("No profile loaded")
        if isinstance(self.profile, dict):
            self.profile = Profile.from_dict(self.profile)
        return self.profile

    def require_tasks(self) -> TaskStore:
        """Return loaded task data or raise if missing."""
        if self.tasks is None:
            raise ValueError("No tasks loaded")
        if isinstance(self.tasks, dict):
            self.tasks = TaskStore.from_dict(self.tasks)
        return self.tasks

    def set_last_list(self, mapping: list[tuple[int, int]]) -> None:
        """Set display-number to task-index mapping for the latest list output."""
        self.last_list = mapping

    def clear_last_list(self) -> None:
        """Clear display-number mapping."""
        self.last_list = []

    def resolve_array_index(self, display_num: int) -> int:
        """Resolve a list/history display number to task array index."""
        if not self.last_list:
            raise ValueError("Run 'list' or 'history' first")

        for current_num, idx in self.last_list:
            if current_num == display_num:
                return idx

        raise ValueError("Invalid task number")

    def get_task_by_display_number(self, display_num: int) -> Task:
        """Get a task via the current list/history display number mapping."""
        array_index = self.resolve_array_index(display_num)
        task = self.require_tasks().get_task_by_index(array_index)
        if not task:
            raise ValueError("Task not found")
        return task
