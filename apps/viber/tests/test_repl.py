"""Tests for command parsing and arity validation."""

import pytest

import viber.repl as repl_module
from viber.command_parser import (
    CommandParseError,
    CreateTaskCommand,
    DeleteEntityCommand,
    HelpCommand,
    ReadEntityCommand,
    ResolveAssignmentCommand,
    UpdateProjectStateCommand,
    ViewEntityCommand,
    WorkEntityCommand,
    parse_command,
)
from viber.commands import execute_command
from viber.models import AssignmentStatus, Database, ProjectState, assignment_key
from viber.service import create_group, create_project, create_task


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


def test_parse_resolve_accepts_p_then_t_order() -> None:
    cmd = parse_command("ok", ["p3", "t5"])
    assert isinstance(cmd, ResolveAssignmentCommand)
    assert cmd.project_id == 3
    assert cmd.task_id == 5
    assert cmd.status == AssignmentStatus.OK


def test_parse_nah_accepts_t_then_p_order() -> None:
    cmd = parse_command("nah", ["t5", "p3"])
    assert isinstance(cmd, ResolveAssignmentCommand)
    assert cmd.project_id == 3
    assert cmd.task_id == 5
    assert cmd.status == AssignmentStatus.NAH


def test_parse_nah_accepts_p_then_t_order() -> None:
    cmd = parse_command("nah", ["p3", "t5"])
    assert isinstance(cmd, ResolveAssignmentCommand)
    assert cmd.project_id == 3
    assert cmd.task_id == 5
    assert cmd.status == AssignmentStatus.NAH


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


def test_parse_create_task_requires_explicit_all_or_group_scope() -> None:
    with pytest.raises(CommandParseError):
        parse_command("create", ["task", "Upgrade deps"])


def test_parse_create_task_with_all_scope() -> None:
    cmd = parse_command("create", ["task", "Upgrade", "deps", "all"])
    assert isinstance(cmd, CreateTaskCommand)
    assert cmd.description == "Upgrade deps"
    assert cmd.group_id is None


def test_parse_create_task_with_group_scope() -> None:
    cmd = parse_command("create", ["task", "Upgrade", "deps", "g12"])
    assert isinstance(cmd, CreateTaskCommand)
    assert cmd.description == "Upgrade deps"
    assert cmd.group_id == 12


def test_parse_create_task_rejects_invalid_scope_token() -> None:
    with pytest.raises(CommandParseError):
        parse_command("create", ["task", "Upgrade", "deps", "backend"])


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


def test_run_loop_aliases_are_mapped_to_full_verbs(monkeypatch: pytest.MonkeyPatch) -> None:
    seen_verbs: list[str] = []
    inputs = iter([
        "c anything",
        "r anything",
        "u anything",
        "d anything",
        "v anything",
        "o anything",
        "n anything",
        "w anything",
        "exit",
    ])

    monkeypatch.setattr("builtins.input", lambda _prompt="": next(inputs))
    monkeypatch.setattr(repl_module, "print_banner", lambda _lines: None)
    monkeypatch.setattr(repl_module, "_record_command_history", lambda _line: None)

    def fake_parse(verb: str, args: list[str]) -> HelpCommand:
        seen_verbs.append(verb)
        return HelpCommand()

    monkeypatch.setattr(repl_module, "parse_command", fake_parse)
    monkeypatch.setattr(
        repl_module, "execute_command", lambda _command, _db, _after_mutation: None
    )

    repl_module._run_loop(Database(), lambda _gids, _removed: None)
    assert seen_verbs == ["create", "read", "update", "delete", "view", "ok", "nah", "work"]


def test_run_loop_quit_is_recognized(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    inputs = iter(["quit"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(inputs))
    monkeypatch.setattr(repl_module, "_record_command_history", lambda _line: None)
    repl_module._run_loop(Database(), lambda _gids, _removed: None)
    out = capsys.readouterr().out
    assert "Goodbye." in out


def test_run_loop_eof_exits_cleanly(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("builtins.input", lambda _prompt="": (_ for _ in ()).throw(EOFError()))
    monkeypatch.setattr(repl_module, "_record_command_history", lambda _line: None)
    repl_module._run_loop(Database(), lambda _gids, _removed: None)
    out = capsys.readouterr().out
    assert "Goodbye." in out


def test_run_loop_unknown_command_shows_helpful_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    inputs = iter(["wat", "exit"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(inputs))
    monkeypatch.setattr(repl_module, "_record_command_history", lambda _line: None)
    repl_module._run_loop(Database(), lambda _gids, _removed: None)
    out = capsys.readouterr().out
    assert "Unknown command: 'wat'. Type 'help' for available commands." in out


def test_run_loop_view_no_pending_shows_expected_message(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    inputs = iter(["view", "exit"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(inputs))
    monkeypatch.setattr(repl_module, "_record_command_history", lambda _line: None)
    repl_module._run_loop(Database(), lambda _gids, _removed: None)
    out = capsys.readouterr().out
    assert "Vibe is good. No pending assignments." in out


def test_work_loop_project_processes_selection_and_quit(monkeypatch: pytest.MonkeyPatch) -> None:
    db = Database()
    g = create_group(db, "Backend")
    p = create_project(db, "api", g.id)
    t1 = create_task(db, "Task A", None)
    t2 = create_task(db, "Task B", None)

    inputs = iter(["2", "o", "", "q"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(inputs))

    execute_command(
        WorkEntityCommand(kind="project", entity_id=p.id),
        db,
        lambda _gids, _removed: None,
    )

    assert db.assignments[assignment_key(p.id, t1.id)].status == AssignmentStatus.PENDING
    assert db.assignments[assignment_key(p.id, t2.id)].status == AssignmentStatus.OK


def test_work_loop_project_cancel_keeps_assignment_pending(monkeypatch: pytest.MonkeyPatch) -> None:
    db = Database()
    g = create_group(db, "Backend")
    p = create_project(db, "api", g.id)
    t = create_task(db, "Task A", None)

    inputs = iter(["1", "c", "q"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(inputs))

    execute_command(
        WorkEntityCommand(kind="project", entity_id=p.id),
        db,
        lambda _gids, _removed: None,
    )

    assert db.assignments[assignment_key(p.id, t.id)].status == AssignmentStatus.PENDING
