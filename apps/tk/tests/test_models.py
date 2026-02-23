"""Tests for typed models and DTO adapters."""

import pytest

from tk.models import (
    HistoryFilters,
    HistoryGroup,
    HistoryListPayload,
    PendingListPayload,
    Profile,
    Task,
    TaskListItem,
    TaskStatus,
    TaskStore,
)


class TestTask:
    """Test task model behavior."""

    def test_task_from_dict_roundtrip(self):
        payload = {
            "text": "Ship feature",
            "status": "done",
            "created_at": "2026-02-23T10:00:00+00:00",
            "handled_at": "2026-02-23T11:00:00+00:00",
            "subjective_date": "2026-02-23",
            "note": "released",
        }

        task = Task.from_dict(payload)
        assert task.to_dict() == payload

    def test_task_invalid_status(self):
        with pytest.raises(ValueError, match="Invalid task status"):
            Task(
                text="Bad",
                status="invalid",
                created_at="2026-02-23T10:00:00+00:00",
            )

    def test_task_dict_compat_setitem(self):
        task = Task(
            text="Before",
            status=TaskStatus.PENDING.value,
            created_at="2026-02-23T10:00:00+00:00",
        )

        task["text"] = "After"
        task["status"] = TaskStatus.DONE.value

        assert task["text"] == "After"
        assert task["status"] == TaskStatus.DONE.value


class TestTaskStore:
    """Test task store behavior."""

    def test_task_store_from_dict_roundtrip(self):
        payload = {
            "tasks": [
                {
                    "text": "Task one",
                    "status": "pending",
                    "created_at": "2026-02-01T10:00:00+00:00",
                    "handled_at": None,
                    "subjective_date": None,
                    "note": None,
                }
            ]
        }

        store = TaskStore.from_dict(payload)
        assert store.to_dict() == payload

    def test_task_store_dict_compat_set_tasks(self):
        store = TaskStore()
        store["tasks"] = [
            {
                "text": "Task one",
                "status": "pending",
                "created_at": "2026-02-01T10:00:00+00:00",
                "handled_at": None,
                "subjective_date": None,
                "note": None,
            }
        ]

        assert len(store.tasks) == 1
        assert store.tasks[0].text == "Task one"

    def test_task_store_update_task(self):
        store = TaskStore.from_dict(
            {
                "tasks": [
                    {
                        "text": "Task one",
                        "status": "pending",
                        "created_at": "2026-02-01T10:00:00+00:00",
                        "handled_at": None,
                        "subjective_date": None,
                        "note": None,
                    }
                ]
            }
        )

        updated = store.update_task(0, status=TaskStatus.DONE.value, note="done")
        assert updated is True
        assert store.tasks[0].status == TaskStatus.DONE.value
        assert store.tasks[0].note == "done"


class TestProfile:
    """Test profile model behavior."""

    def test_profile_from_dict_defaults(self):
        profile = Profile.from_dict(
            {
                "timezone": "Asia/Tokyo",
                "subjective_day_start": "04:00:00",
                "data_path": "/tmp/tasks.json",
                "output_path": "/tmp/TODO.md",
            }
        )

        assert profile.auto_sync is True
        assert profile.sync_on_exit is False

    def test_profile_dict_compat(self):
        profile = Profile.from_dict(
            {
                "timezone": "Asia/Tokyo",
                "subjective_day_start": "04:00:00",
                "data_path": "/tmp/tasks.json",
                "output_path": "/tmp/TODO.md",
                "auto_sync": False,
                "sync_on_exit": True,
            }
        )

        profile["auto_sync"] = True
        assert profile["auto_sync"] is True
        assert profile.get("timezone") == "Asia/Tokyo"


class TestPayloadDtos:
    """Test presenter payload DTOs."""

    def test_pending_payload_dict_compat(self):
        task = Task(
            text="Task one",
            status=TaskStatus.PENDING.value,
            created_at="2026-02-01T10:00:00+00:00",
        )
        payload = PendingListPayload(
            items=[TaskListItem(display_num=1, array_index=0, task=task)]
        )

        assert "items" in payload
        assert payload["items"][0]["display_num"] == 1
        assert payload["items"][0]["task"]["text"] == "Task one"

    def test_history_payload_dict_compat(self):
        task = Task(
            text="Task two",
            status=TaskStatus.DONE.value,
            created_at="2026-02-02T10:00:00+00:00",
            handled_at="2026-02-02T15:00:00+00:00",
            subjective_date="2026-02-02",
        )
        payload = HistoryListPayload(
            groups=[
                HistoryGroup(
                    date="2026-02-02",
                    items=[TaskListItem(display_num=1, array_index=0, task=task)],
                )
            ],
            filters=HistoryFilters(days=7),
        )

        assert payload["groups"][0]["date"] == "2026-02-02"
        assert payload["filters"].get("days") == 7
