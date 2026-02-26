"""Tests for command parsing and arity validation."""

import pytest

from viber.command_parser import (
    CommandParseError,
    DeleteEntityCommand,
    ReadEntityCommand,
    ResolveAssignmentCommand,
    UpdateProjectStateCommand,
    ViewEntityCommand,
    WorkEntityCommand,
    parse_command,
)
from viber.models import AssignmentStatus, ProjectState


def test_parse_read_entity_project() -> None:
    cmd = parse_command("read", ["p12"])
    assert isinstance(cmd, ReadEntityCommand)
    assert cmd.kind == "project"
    assert cmd.entity_id == 12


def test_parse_view_entity_task() -> None:
    cmd = parse_command("view", ["t5"])
    assert isinstance(cmd, ViewEntityCommand)
    assert cmd.kind == "task"
    assert cmd.entity_id == 5


def test_parse_work_entity_project() -> None:
    cmd = parse_command("work", ["p3"])
    assert isinstance(cmd, WorkEntityCommand)
    assert cmd.kind == "project"
    assert cmd.entity_id == 3


def test_parse_resolve_accepts_t_then_p_order() -> None:
    cmd = parse_command("ok", ["t5", "p3"])
    assert isinstance(cmd, ResolveAssignmentCommand)
    assert cmd.project_id == 3
    assert cmd.task_id == 5
    assert cmd.status == AssignmentStatus.OK


def test_parse_delete_single_target() -> None:
    cmd = parse_command("delete", ["g1"])
    assert isinstance(cmd, DeleteEntityCommand)
    assert cmd.kind == "group"
    assert cmd.entity_id == 1


def test_parse_update_project_state() -> None:
    cmd = parse_command("update", ["p1", "state", "suspended"])
    assert isinstance(cmd, UpdateProjectStateCommand)
    assert cmd.project_id == 1
    assert cmd.new_state == ProjectState.SUSPENDED


def test_parse_rejects_extra_arg_for_read() -> None:
    with pytest.raises(CommandParseError):
        parse_command("read", ["projects", "extra"])


def test_parse_rejects_extra_arg_for_delete() -> None:
    with pytest.raises(CommandParseError):
        parse_command("delete", ["t1", "extra"])


def test_parse_rejects_extra_arg_for_view() -> None:
    with pytest.raises(CommandParseError):
        parse_command("view", ["p1", "extra"])


def test_parse_rejects_extra_arg_for_work() -> None:
    with pytest.raises(CommandParseError):
        parse_command("work", ["t1", "extra"])


def test_parse_rejects_extra_arg_for_ok() -> None:
    with pytest.raises(CommandParseError):
        parse_command("ok", ["p1", "t2", "extra"])


def test_parse_rejects_extra_arg_for_update_state() -> None:
    with pytest.raises(CommandParseError):
        parse_command("update", ["p1", "state", "active", "extra"])


def test_parse_rejects_update_project_state_shorthand() -> None:
    with pytest.raises(CommandParseError):
        parse_command("update", ["p1", "active"])


def test_parse_rejects_update_project_name_shorthand() -> None:
    with pytest.raises(CommandParseError):
        parse_command("update", ["p1", "new-name"])
