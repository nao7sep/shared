"""Business command logic for tk."""

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from tk import data, markdown, subjective_date
from tk.errors import UsageError, ValidationError
from tk.models import (
    HistoryFilters,
    HistoryGroup,
    HistoryListPayload,
    PendingListPayload,
    Task,
    TaskListItem,
    TaskStatus,
)
from tk.session import Session
from tk.validation import validate_date_format

_HANDLED_STATUSES = (TaskStatus.DONE, TaskStatus.CANCELLED)


def _validate_positive_int(name: str, value: int | None) -> None:
    """Validate optional integer filters that must be positive."""
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValidationError(f"{name} must be a positive integer")


def _sync_if_auto(session: Session) -> None:
    """Regenerate TODO.md if auto_sync is enabled."""
    prof = session.require_profile()
    tasks_data = session.require_tasks()

    if prof.auto_sync:
        markdown.generate_todo(tasks_data.tasks, prof.output_path)


def get_default_subjective_date(session: Session) -> str:
    """Get current subjective date for the active profile settings."""
    prof = session.require_profile()
    return subjective_date.get_current_subjective_date(
        prof.timezone,
        prof.subjective_day_start,
    )


def list_pending_data(session: Session) -> PendingListPayload:
    """Return structured pending task data for presentation layers."""
    tasks_data = session.require_tasks()

    pending_with_indices = [
        (i, task)
        for i, task in enumerate(tasks_data.tasks)
        if task.status == TaskStatus.PENDING
    ]
    pending_with_indices.sort(key=lambda x: x[1].created_utc)

    items: list[TaskListItem] = []
    for display_num, (array_index, task) in enumerate(pending_with_indices, start=1):
        items.append(
            TaskListItem(
                display_num=display_num,
                array_index=array_index,
                task=task,
            )
        )

    return PendingListPayload(items=items)


def list_history_data(
    session: Session,
    days: int | None = None,
    working_days: int | None = None,
    specific_date: str | None = None,
) -> HistoryListPayload:
    """Return structured handled task data for presentation layers."""
    _validate_positive_int("days", days)
    _validate_positive_int("working_days", working_days)

    filters_specified = sum(
        [days is not None, working_days is not None, specific_date is not None]
    )
    if filters_specified > 1:
        raise UsageError("Cannot specify multiple filters (--days, --working-days, or specific_date)")

    tasks_data = session.require_tasks()
    handled_with_indices = [
        (i, task)
        for i, task in enumerate(tasks_data.tasks)
        if task.status in _HANDLED_STATUSES
    ]

    if days is not None:
        from datetime import date as date_type, timedelta

        current_subjective = get_default_subjective_date(session)
        today = date_type.fromisoformat(current_subjective)
        cutoff = today - timedelta(days=days - 1)

        handled_with_indices = [
            (i, t)
            for i, t in handled_with_indices
            if t.subjective_date and t.subjective_date >= cutoff.isoformat()
        ]

    elif working_days is not None:
        by_date: dict[str, list[tuple[int, Task]]] = defaultdict(list)
        for i, task in handled_with_indices:
            date_str = task.subjective_date
            if date_str:
                by_date[date_str].append((i, task))

        sorted_dates = sorted(by_date.keys(), reverse=True)
        dates_to_include = sorted_dates[:working_days]

        handled_with_indices = [
            (i, t)
            for i, t in handled_with_indices
            if t.subjective_date in dates_to_include
        ]

    elif specific_date is not None:
        handled_with_indices = [
            (i, t)
            for i, t in handled_with_indices
            if t.subjective_date == specific_date
        ]

    groups: list[HistoryGroup] = []
    display_num = 1
    grouped = data.group_handled_tasks(handled_with_indices, include_unknown=True)
    for date_str, date_items in grouped:
        items: list[TaskListItem] = []
        for array_index, task in date_items:
            items.append(
                TaskListItem(
                    display_num=display_num,
                    array_index=array_index,
                    task=task,
                )
            )
            display_num += 1

        groups.append(HistoryGroup(date=date_str, items=items))

    return HistoryListPayload(
        groups=groups,
        filters=HistoryFilters(
            days=days,
            working_days=working_days,
            specific_date=specific_date,
        ),
    )


def extract_last_list_mapping(
    payload: PendingListPayload | HistoryListPayload,
) -> list[tuple[int, int]]:
    """Build (display_num, array_index) mapping from list/history payloads."""
    if isinstance(payload, PendingListPayload):
        return [(item.display_num, item.array_index) for item in payload.items]

    mapping: list[tuple[int, int]] = []
    for group in payload.groups:
        mapping.extend((item.display_num, item.array_index) for item in group.items)
    return mapping


def cmd_add(session: Session, text: str) -> str:
    """Add a new pending task."""
    if not text.strip():
        raise ValidationError("Task text cannot be empty")

    tasks_data = session.require_tasks()
    prof = session.require_profile()

    tasks_data.add_task(text)
    data.save_tasks(prof.data_path, tasks_data)
    _sync_if_auto(session)

    return "Task added."


def _handle_task(
    session: Session,
    array_index: int,
    status: TaskStatus,
    note: str | None,
    date_str: str | None,
) -> str:
    """Mark a task as handled."""
    subj_date = date_str if date_str else get_default_subjective_date(session)
    validate_date_format(subj_date)

    tasks_data = session.require_tasks()
    prof = session.require_profile()

    now_utc = datetime.now(timezone.utc).isoformat()
    updated = tasks_data.update_task(
        array_index,
        status=status,
        handled_utc=now_utc,
        subjective_date=subj_date,
        note=note,
    )
    if not updated:
        raise UsageError("Task not found")

    data.save_tasks(prof.data_path, tasks_data)
    _sync_if_auto(session)

    return f"Task marked as {status.value}."


def cmd_done(
    session: Session,
    array_index: int,
    note: str | None = None,
    date_str: str | None = None,
) -> str:
    """Mark a task as done."""
    return _handle_task(session, array_index, TaskStatus.DONE, note, date_str)


def cmd_cancel(
    session: Session,
    array_index: int,
    note: str | None = None,
    date_str: str | None = None,
) -> str:
    """Mark a task as cancelled."""
    return _handle_task(session, array_index, TaskStatus.CANCELLED, note, date_str)


def cmd_edit(session: Session, array_index: int, text: str) -> str:
    """Edit task text."""
    if not text.strip():
        raise ValidationError("Task text cannot be empty")

    tasks_data = session.require_tasks()
    prof = session.require_profile()

    if not tasks_data.update_task(array_index, text=text):
        raise UsageError("Task not found")

    data.save_tasks(prof.data_path, tasks_data)
    _sync_if_auto(session)

    return "Task updated."


def cmd_delete(session: Session, array_index: int, confirm: bool = False) -> str:
    """Delete task permanently."""
    tasks_data = session.require_tasks()
    prof = session.require_profile()

    if not tasks_data.get_task_by_index(array_index):
        raise UsageError("Task not found")

    if not confirm:
        return "Deletion cancelled."

    if not tasks_data.delete_task(array_index):
        raise UsageError("Task not found")

    data.save_tasks(prof.data_path, tasks_data)
    _sync_if_auto(session)

    return "Task deleted."


def cmd_note(session: Session, array_index: int, note: str | None = None) -> str:
    """Set, update, or remove note on a task."""
    tasks_data = session.require_tasks()
    prof = session.require_profile()

    task = tasks_data.get_task_by_index(array_index)
    if not task:
        raise UsageError("Task not found")
    if task.status == TaskStatus.PENDING:
        raise ValidationError("Cannot set note on pending task. Mark it done or cancelled first.")

    if not tasks_data.update_task(array_index, note=note):
        raise UsageError("Task not found")

    data.save_tasks(prof.data_path, tasks_data)
    _sync_if_auto(session)

    return "Note updated." if note else "Note removed."


def cmd_date(session: Session, array_index: int, date_str: str) -> str:
    """Change subjective handling date on a handled task."""
    validate_date_format(date_str)

    tasks_data = session.require_tasks()
    prof = session.require_profile()

    task = tasks_data.get_task_by_index(array_index)
    if not task:
        raise UsageError("Task not found")
    if task.status == TaskStatus.PENDING:
        raise ValidationError("Cannot set date on pending task. Mark it done or cancelled first.")

    if not tasks_data.update_task(array_index, subjective_date=date_str):
        raise UsageError("Task not found")

    data.save_tasks(prof.data_path, tasks_data)
    _sync_if_auto(session)

    return f"Subjective date updated to {date_str}."


def cmd_sync(session: Session) -> str:
    """Regenerate TODO.md from current data."""
    prof = session.require_profile()
    tasks_data = session.require_tasks()

    output_path = prof.output_path
    markdown.generate_todo(tasks_data.tasks, output_path)

    filename = Path(output_path).name
    return f"{filename} regenerated."


def cmd_today_data(session: Session) -> HistoryListPayload:
    """Return history payload for current subjective date."""
    return list_history_data(session, specific_date=get_default_subjective_date(session))


def cmd_yesterday_data(session: Session) -> HistoryListPayload:
    """Return history payload for yesterday's subjective date."""
    from datetime import date as date_type, timedelta

    today = date_type.fromisoformat(get_default_subjective_date(session))
    yesterday = (today - timedelta(days=1)).isoformat()
    return list_history_data(session, specific_date=yesterday)


def cmd_recent_data(session: Session) -> HistoryListPayload:
    """Return history payload for last 3 working days."""
    return list_history_data(session, working_days=3)
