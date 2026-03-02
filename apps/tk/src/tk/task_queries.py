"""Task grouping and read-model helpers for presentation layers."""

from tk.models import (
    GroupedTaskDisplay,
    HistoryGroup,
    Task,
    TaskListItem,
    TaskStatus,
)


def group_tasks_for_display(tasks: list[Task]) -> GroupedTaskDisplay:
    """Group and sort tasks for TODO/history display."""
    pending: list[Task] = [task for task in tasks if task.status == TaskStatus.PENDING]
    pending.sort(key=lambda t: t.created_utc)

    done_groups: list[tuple[str, list[Task]]] = []
    cancelled_groups: list[tuple[str, list[Task]]] = []

    for status, target in ((TaskStatus.DONE, done_groups), (TaskStatus.CANCELLED, cancelled_groups)):
        handled_with_indices = [
            (i, task)
            for i, task in enumerate(tasks)
            if task.status == status
        ]
        grouped = group_handled_tasks(handled_with_indices, include_unknown=True)
        target.extend(
            (group.date, [item.task for item in group.items]) for group in grouped
        )

    return GroupedTaskDisplay(pending=pending, done=done_groups, cancelled=cancelled_groups)


def group_handled_tasks(
    handled_with_indices: list[tuple[int, Task]],
    *,
    include_unknown: bool,
) -> list[HistoryGroup]:
    """Group handled tasks by subjective date with deterministic ordering."""
    grouped: dict[str, list[TaskListItem]] = {}

    for array_index, task in handled_with_indices:
        date = task.subjective_date
        if not date:
            if not include_unknown:
                continue
            date = "unknown"

        if date not in grouped:
            grouped[date] = []
        grouped[date].append(TaskListItem(array_index=array_index, task=task))

    for date in grouped:
        grouped[date].sort(key=lambda item: item.task.handled_utc or "")

    known = sorted(
        [
            HistoryGroup(date=date, items=items)
            for date, items in grouped.items()
            if date != "unknown"
        ],
        key=lambda g: g.date,
        reverse=True,
    )
    if "unknown" in grouped:
        known.append(HistoryGroup(date="unknown", items=grouped["unknown"]))
    return known
