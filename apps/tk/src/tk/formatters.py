"""Text formatters for REPL output."""

from tk.models import HistoryListPayload, PendingListPayload, TaskStatus


def format_pending_list(payload: PendingListPayload) -> str:
    """Render pending list payload to CLI text."""
    items = payload.items
    if not items:
        return "No pending tasks."

    total_count = len(items)
    num_width = len(str(total_count))

    lines = []
    for item in items:
        padded_num = str(item.display_num).rjust(num_width)
        lines.append(f"{padded_num}. {item.task.text}")

    return "\n".join(lines)


def format_history_list(payload: HistoryListPayload) -> str:
    """Render history payload to CLI text."""
    groups = payload.groups
    filters = payload.filters

    if not groups:
        if filters.days is not None:
            return f"No handled tasks in last {filters.days} days."
        if filters.working_days is not None:
            return f"No handled tasks in last {filters.working_days} working days."
        if filters.specific_date is not None:
            return f"No handled tasks on {filters.specific_date}."
        return "No handled tasks."

    total_count = sum(len(group.items) for group in groups)
    num_width = len(str(total_count))

    lines: list[str] = []
    for group_index, group in enumerate(groups):
        lines.append(group.date)

        for item in group.items:
            task = item.task
            status_emoji = "✅" if task.status == TaskStatus.DONE.value else "❌"
            padded_num = str(item.display_num).rjust(num_width)

            if task.note:
                lines.append(f"  {padded_num}. {status_emoji} {task.text} => {task.note}")
            else:
                lines.append(f"  {padded_num}. {status_emoji} {task.text}")

        if group_index < len(groups) - 1:
            lines.append("")

    return "\n".join(lines)
