"""Tests for CLI output formatters."""

import pytest

from tk import formatters
from tk.models import HistoryFilters, HistoryGroup, HistoryListPayload, PendingListPayload, Task, TaskListItem


def _task(text: str, status: str, *, note: str | None = None) -> Task:
    return Task(
        text=text,
        status=status,
        created_utc="2026-02-09T10:00:00+00:00",
        handled_utc="2026-02-09T11:00:00+00:00" if status != "pending" else None,
        subjective_date="2026-02-09" if status != "pending" else None,
        note=note,
    )


class TestFormatPendingList:
    """Test pending task list formatting."""

    def test_format_pending_list_empty(self):
        """Test empty pending list message."""
        assert formatters.format_pending_list(PendingListPayload()) == "No pending tasks."

    def test_format_pending_list_aligns_multi_digit_numbers(self):
        """Test that pending numbering stays aligned after 9 items."""
        payload = PendingListPayload(
            items=[
                TaskListItem(display_num=index, array_index=index - 1, task=_task(f"Task {index}", "pending"))
                for index in range(1, 13)
            ]
        )

        lines = formatters.format_pending_list(payload).splitlines()
        assert lines[0] == " 1. Task 1"
        assert lines[8] == " 9. Task 9"
        assert lines[9] == "10. Task 10"


class TestFormatHistoryList:
    """Test handled task history formatting."""

    @pytest.mark.parametrize(
        ("filters", "expected"),
        [
            (HistoryFilters(days=7), "No handled tasks in last 7 days."),
            (HistoryFilters(working_days=3), "No handled tasks in last 3 working days."),
            (HistoryFilters(specific_date="2026-02-09"), "No handled tasks on 2026-02-09."),
            (HistoryFilters(), "No handled tasks."),
        ],
    )
    def test_format_history_list_empty_messages(self, filters, expected):
        """Test empty-state messages for each history filter mode."""
        payload = HistoryListPayload(groups=[], filters=filters)

        assert formatters.format_history_list(payload) == expected

    def test_format_history_list_renders_status_notes_and_group_spacing(self):
        """Test mixed handled tasks formatting with notes and date group spacing."""
        payload = HistoryListPayload(
            groups=[
                HistoryGroup(
                    date="2026-02-09",
                    items=[
                        TaskListItem(display_num=1, array_index=0, task=_task("Shipped", "done")),
                        TaskListItem(display_num=2, array_index=1, task=_task("Deferred", "cancelled", note="Blocked")),
                    ],
                ),
                HistoryGroup(
                    date="2026-02-08",
                    items=[
                        TaskListItem(display_num=3, array_index=2, task=_task("Documented", "done", note="Wiki updated")),
                    ],
                ),
            ],
            filters=HistoryFilters(),
        )

        assert formatters.format_history_list(payload) == (
            "2026-02-09\n"
            "  1. ✅ Shipped\n"
            "  2. ❌ Deferred => Blocked\n"
            "\n"
            "2026-02-08\n"
            "  3. ✅ Documented => Wiki updated"
        )

    def test_format_history_list_aligns_multi_digit_numbers(self):
        """Test that history numbering stays aligned when there are 10+ rows."""
        payload = HistoryListPayload(
            groups=[
                HistoryGroup(
                    date="2026-02-09",
                    items=[
                        TaskListItem(display_num=index, array_index=index - 1, task=_task(f"Task {index}", "done"))
                        for index in range(1, 11)
                    ],
                )
            ],
            filters=HistoryFilters(),
        )

        lines = formatters.format_history_list(payload).splitlines()
        assert lines[1] == "   1. ✅ Task 1"
        assert lines[-1] == "  10. ✅ Task 10"
