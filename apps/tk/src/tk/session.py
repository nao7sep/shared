"""Session state container for tk runtime."""

from dataclasses import dataclass, field

from tk.errors import UsageError
from tk.models import Profile, Task, TaskListItem, TaskStore


@dataclass
class Session:
    """In-memory runtime state for a tk session."""

    profile_path: str | None = None
    profile: Profile | None = None
    tasks: TaskStore | None = None
    last_list: list[TaskListItem] = field(default_factory=list)

    def require_profile(self) -> Profile:
        """Return loaded profile or raise if missing."""
        if self.profile is None:
            raise UsageError("No profile loaded")
        return self.profile

    def require_tasks(self) -> TaskStore:
        """Return loaded task data or raise if missing."""
        if self.tasks is None:
            raise UsageError("No tasks loaded")
        return self.tasks

    def set_last_list(self, items: list[TaskListItem]) -> None:
        """Set display-number to task-index mapping for the latest list output."""
        self.last_list = items

    def clear_last_list(self) -> None:
        """Clear display-number mapping."""
        self.last_list = []

    def _find_item(self, display_num: int) -> TaskListItem:
        """Look up a TaskListItem by its display number."""
        if not self.last_list:
            raise UsageError("Run 'list' or 'history' first")

        for item in self.last_list:
            if item.display_num == display_num:
                return item

        raise UsageError("Invalid task number")

    def resolve_array_index(self, display_num: int) -> int:
        """Resolve a list/history display number to task array index."""
        return self._find_item(display_num).array_index

    def get_task_by_display_number(self, display_num: int) -> Task:
        """Get a task via the current list/history display number mapping."""
        return self._find_item(display_num).task
