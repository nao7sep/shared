"""Tests for commands module."""

import pytest
from freezegun import freeze_time

from tk import commands
from tk.errors import UsageError, ValidationError
from tk.models import HistoryListPayload, Task, TaskStore


class TestListPendingData:
    """Test list_pending_data function."""

    def test_list_pending_data_empty(self, sample_session):
        """Test listing pending tasks when none exist."""
        sample_session.tasks = TaskStore()

        result = commands.list_pending_data(sample_session)

        assert result.items == []

    def test_list_pending_data_multiple_tasks(self, sample_session):
        """Test listing multiple pending tasks."""
        result = commands.list_pending_data(sample_session)

        items = result.items
        assert len(items) == 1  # Only one pending task
        assert items[0].display_num == 1
        assert items[0].task.text == "Task one"

    def test_list_pending_data_sorts_by_created_utc(self, sample_session):
        """Test that pending tasks are sorted by created_utc."""
        sample_session.tasks = TaskStore(tasks=[
            Task(text="Third", status="pending", created_utc="2026-02-03T10:00:00+00:00"),
            Task(text="First", status="pending", created_utc="2026-02-01T10:00:00+00:00"),
            Task(text="Second", status="pending", created_utc="2026-02-02T10:00:00+00:00"),
        ])

        result = commands.list_pending_data(sample_session)

        items = result.items
        assert items[0].task.text == "First"
        assert items[1].task.text == "Second"
        assert items[2].task.text == "Third"

    def test_list_pending_data_filters_handled(self, sample_session):
        """Test that done/cancelled tasks are excluded."""
        result = commands.list_pending_data(sample_session)

        # sample_session has 1 pending, 1 done, 1 cancelled
        items = result.items
        assert len(items) == 1
        assert all(item.task.status == "pending" for item in items)


class TestListHistoryData:
    """Test list_history_data function."""

    def test_list_history_data_empty(self, sample_session):
        """Test listing history when no handled tasks exist."""
        sample_session.tasks = TaskStore()

        result = commands.list_history_data(sample_session)

        assert result.groups == []

    @freeze_time("2026-02-09 10:00:00", tz_offset=0)
    def test_list_history_data_days_filter(self, sample_session):
        """Test filtering history by days."""
        # Add task from 10 days ago
        sample_session.tasks.tasks.append(Task(
            text="Old task",
            status="done",
            created_utc="2026-01-30T10:00:00+00:00",
            handled_utc="2026-01-30T15:00:00+00:00",
            subjective_date="2026-01-30",
            note=None,
        ))

        result = commands.list_history_data(sample_session, days=7)

        # Should not include the old task
        groups = result.groups
        dates = [g.date for g in groups]
        assert "2026-01-30" not in dates

    def test_list_history_data_working_days_filter(self, sample_session):
        """Test filtering history by working days."""
        result = commands.list_history_data(sample_session, working_days=1)

        # Should only include latest working day
        groups = result.groups
        assert len(groups) == 1

    def test_list_history_data_specific_date_filter(self, sample_session):
        """Test filtering history by specific date."""
        result = commands.list_history_data(sample_session, specific_date="2026-02-02")

        groups = result.groups
        assert len(groups) == 1
        assert groups[0].date == "2026-02-02"

    def test_list_history_data_multiple_filters_error(self, sample_session):
        """Test that multiple filters raise ValueError."""
        with pytest.raises(UsageError, match="Cannot specify multiple filters"):
            commands.list_history_data(sample_session, days=7, working_days=3)

    @pytest.mark.parametrize(
        ("kwargs", "expected_message"),
        [
            ({"days": 0}, "days must be a positive integer"),
            ({"days": -1}, "days must be a positive integer"),
            ({"days": "7"}, "days must be a positive integer"),
            ({"working_days": 0}, "working_days must be a positive integer"),
            ({"working_days": True}, "working_days must be a positive integer"),
        ],
    )
    def test_list_history_data_rejects_non_positive_filters(self, sample_session, kwargs, expected_message):
        """Test that history filters must be positive integers."""
        with pytest.raises(ValidationError, match=expected_message):
            commands.list_history_data(sample_session, **kwargs)

    def test_list_history_data_flattens_display_numbers_across_groups(self, sample_session):
        """Test display numbering and array-index mapping across date groups."""
        sample_session.tasks.tasks.append(Task(
            text="Task four",
            status="done",
            created_utc="2026-02-03T09:00:00+00:00",
            handled_utc="2026-02-03T10:00:00+00:00",
            subjective_date="2026-02-03",
            note="Earlier same day",
        ))

        result = commands.list_history_data(sample_session)

        assert [group.date for group in result.groups] == ["2026-02-03", "2026-02-02"]
        assert [item.task.text for item in result.groups[0].items] == ["Task four", "Task three"]
        assert [item.display_num for group in result.groups for item in group.items] == [1, 2, 3]
        assert commands.extract_last_list_mapping(result) == [(1, 3), (2, 2), (3, 1)]


class TestCmdAdd:
    """Test cmd_add function."""

    def test_cmd_add_creates_task(self, sample_session, temp_dir):
        """Test that cmd_add creates task."""
        result = commands.cmd_add(sample_session, "New task")

        assert result == "Task added."
        assert len(sample_session.tasks.tasks) == 4

    def test_cmd_add_empty_text_error(self, sample_session):
        """Test that empty text raises ValueError."""
        with pytest.raises(ValidationError, match="Task text cannot be empty"):
            commands.cmd_add(sample_session, "")

        with pytest.raises(ValidationError, match="Task text cannot be empty"):
            commands.cmd_add(sample_session, "   ")

    def test_cmd_add_syncs_if_auto(self, sample_session, temp_dir):
        """Test that cmd_add syncs when auto_sync is true."""
        sample_session.profile.auto_sync = True

        commands.cmd_add(sample_session, "New task")

        # Check that TODO.md was created
        output_path = sample_session.profile.output_path
        import os
        assert os.path.exists(output_path)


class TestCmdDone:
    """Test cmd_done function."""

    @freeze_time("2026-02-09 10:00:00", tz_offset=0)
    def test_cmd_done_marks_task(self, sample_session):
        """Test that cmd_done sets status to 'done'."""
        commands.cmd_done(sample_session, 0)

        task = sample_session.tasks.tasks[0]
        assert task.status == "done"

    @freeze_time("2026-02-09 10:00:00", tz_offset=0)
    def test_cmd_done_sets_handled_utc(self, sample_session):
        """Test that cmd_done sets handled_utc timestamp."""
        commands.cmd_done(sample_session, 0)

        task = sample_session.tasks.tasks[0]
        assert task.handled_utc is not None
        assert "2026-02-09" in task.handled_utc

    @freeze_time("2026-02-09 10:00:00", tz_offset=0)
    def test_cmd_done_sets_subjective_date(self, sample_session):
        """Test that cmd_done sets subjective_date."""
        commands.cmd_done(sample_session, 0)

        task = sample_session.tasks.tasks[0]
        assert task.subjective_date is not None

    def test_cmd_done_with_note(self, sample_session):
        """Test that cmd_done saves note."""
        commands.cmd_done(sample_session, 0, note="Test note")

        task = sample_session.tasks.tasks[0]
        assert task.note == "Test note"

    def test_cmd_done_with_custom_date(self, sample_session):
        """Test that cmd_done uses provided date."""
        commands.cmd_done(sample_session, 0, date_str="2026-02-05")

        task = sample_session.tasks.tasks[0]
        assert task.subjective_date == "2026-02-05"

    def test_cmd_done_invalid_index_error(self, sample_session):
        """Test that invalid index raises ValueError."""
        with pytest.raises(UsageError, match="Task not found"):
            commands.cmd_done(sample_session, 999)


class TestCmdCancel:
    """Test cmd_cancel function."""

    def test_cmd_cancel_marks_task(self, sample_session):
        """Test that cmd_cancel sets status to 'cancelled'."""
        commands.cmd_cancel(sample_session, 0)

        task = sample_session.tasks.tasks[0]
        assert task.status == "cancelled"

    def test_cmd_cancel_with_note(self, sample_session):
        """Test that cmd_cancel saves note."""
        commands.cmd_cancel(sample_session, 0, note="Not needed")

        task = sample_session.tasks.tasks[0]
        assert task.note == "Not needed"


class TestCmdEdit:
    """Test cmd_edit function."""

    def test_cmd_edit_changes_text(self, sample_session):
        """Test that cmd_edit updates text."""
        commands.cmd_edit(sample_session, 0, "Updated text")

        task = sample_session.tasks.tasks[0]
        assert task.text == "Updated text"

    def test_cmd_edit_empty_text_error(self, sample_session):
        """Test that empty text raises ValueError."""
        with pytest.raises(ValidationError, match="Task text cannot be empty"):
            commands.cmd_edit(sample_session, 0, "")

    def test_cmd_edit_invalid_index_error(self, sample_session):
        """Test that invalid index raises ValueError."""
        with pytest.raises(UsageError, match="Task not found"):
            commands.cmd_edit(sample_session, 999, "New text")


class TestCmdDelete:
    """Test cmd_delete function."""

    def test_cmd_delete_without_confirm(self, sample_session):
        """Test that deletion without confirm is cancelled."""
        result = commands.cmd_delete(sample_session, 0, confirm=False)

        assert result == "Deletion cancelled."
        assert len(sample_session.tasks.tasks) == 3

    def test_cmd_delete_with_confirm(self, sample_session):
        """Test that deletion with confirm removes task."""
        result = commands.cmd_delete(sample_session, 0, confirm=True)

        assert result == "Task deleted."
        assert len(sample_session.tasks.tasks) == 2

    def test_cmd_delete_invalid_index_error(self, sample_session):
        """Test that invalid index raises ValueError."""
        with pytest.raises(UsageError, match="Task not found"):
            commands.cmd_delete(sample_session, 999, confirm=True)


class TestCmdNote:
    """Test cmd_note function."""

    def test_cmd_note_sets_note(self, sample_session):
        """Test that cmd_note sets note."""
        # Task at index 1 is done
        commands.cmd_note(sample_session, 1, "New note")

        task = sample_session.tasks.tasks[1]
        assert task.note == "New note"

    def test_cmd_note_removes_note(self, sample_session):
        """Test that cmd_note removes note when None."""
        # First set a note
        commands.cmd_note(sample_session, 1, "Test note")
        assert sample_session.tasks.tasks[1].note == "Test note"

        # Then remove it
        result = commands.cmd_note(sample_session, 1, None)

        assert result == "Note removed."
        assert sample_session.tasks.tasks[1].note is None

    def test_cmd_note_invalid_index_error(self, sample_session):
        """Test that invalid index raises ValueError."""
        with pytest.raises(UsageError, match="Task not found"):
            commands.cmd_note(sample_session, 999, "Note")

    def test_cmd_note_pending_task_error(self, sample_session):
        """Test that setting note on pending task raises ValueError."""
        # Task at index 0 is pending
        with pytest.raises(ValidationError, match="Cannot set note on pending task"):
            commands.cmd_note(sample_session, 0, "Note")


class TestCmdDate:
    """Test cmd_date function."""

    def test_cmd_date_changes_date(self, sample_session):
        """Test that cmd_date updates subjective_date."""
        # Task at index 1 is done
        commands.cmd_date(sample_session, 1, "2026-02-05")

        task = sample_session.tasks.tasks[1]
        assert task.subjective_date == "2026-02-05"

    def test_cmd_date_invalid_format_error(self, sample_session):
        """Test that invalid date format raises ValueError."""
        with pytest.raises(ValidationError, match="Invalid date"):
            commands.cmd_date(sample_session, 1, "02-05-2026")

    def test_cmd_date_pending_task_error(self, sample_session):
        """Test that changing date on pending task raises ValueError."""
        # Task at index 0 is pending
        with pytest.raises(ValidationError, match="Cannot set date on pending task"):
            commands.cmd_date(sample_session, 0, "2026-02-05")


class TestCmdSync:
    """Test cmd_sync function."""

    def test_cmd_sync_generates_markdown(self, sample_session, temp_dir):
        """Test that cmd_sync calls generate_todo."""
        result = commands.cmd_sync(sample_session)

        assert "regenerated" in result
        # Check that file was created
        import os
        assert os.path.exists(sample_session.profile.output_path)


class TestHistoryShortcutCommands:
    """Test history convenience commands."""

    def test_cmd_today_data_uses_current_subjective_date(self, sample_session, monkeypatch):
        """Test that today delegates to history with today's subjective date."""
        payload = HistoryListPayload()
        captured: dict[str, object] = {}

        monkeypatch.setattr(commands, "get_default_subjective_date", lambda session: "2026-02-09")

        def fake_list_history_data(session, days=None, working_days=None, specific_date=None):
            captured["call"] = (session, days, working_days, specific_date)
            return payload

        monkeypatch.setattr(commands, "list_history_data", fake_list_history_data)

        result = commands.cmd_today_data(sample_session)

        assert result is payload
        assert captured["call"] == (sample_session, None, None, "2026-02-09")

    def test_cmd_yesterday_data_uses_previous_subjective_date(self, sample_session, monkeypatch):
        """Test that yesterday delegates to history with the previous date."""
        payload = HistoryListPayload()
        captured: dict[str, object] = {}

        monkeypatch.setattr(commands, "get_default_subjective_date", lambda session: "2026-02-09")

        def fake_list_history_data(session, days=None, working_days=None, specific_date=None):
            captured["call"] = (session, days, working_days, specific_date)
            return payload

        monkeypatch.setattr(commands, "list_history_data", fake_list_history_data)

        result = commands.cmd_yesterday_data(sample_session)

        assert result is payload
        assert captured["call"] == (sample_session, None, None, "2026-02-08")

    def test_cmd_recent_data_uses_three_working_days(self, sample_session, monkeypatch):
        """Test that recent delegates to history with the fixed 3-day window."""
        payload = HistoryListPayload()
        captured: dict[str, object] = {}

        def fake_list_history_data(session, days=None, working_days=None, specific_date=None):
            captured["call"] = (session, days, working_days, specific_date)
            return payload

        monkeypatch.setattr(commands, "list_history_data", fake_list_history_data)

        result = commands.cmd_recent_data(sample_session)

        assert result is payload
        assert captured["call"] == (sample_session, None, 3, None)
