"""Tests for command parsing and arity validation."""

from pathlib import Path

import pytest

import viber.repl as repl_module
from viber.command_parser import (
    CommandParseError,
    CreateTaskCommand,
    DeleteEntityCommand,
    HelpCommand,
    ReadEntityCommand,
    ResolveAssignmentCommand,
    UndoAssignmentCommand,
    UndoEntityCommand,
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
        "z anything",
        "exit",
    ])

    monkeypatch.setattr("builtins.input", lambda _prompt="": next(inputs))

    def fake_parse(verb: str, args: list[str]) -> HelpCommand:
        seen_verbs.append(verb)
        return HelpCommand()

    monkeypatch.setattr(repl_module, "parse_command", fake_parse)
    monkeypatch.setattr(
        repl_module, "execute_command", lambda _command, _db, _after_mutation: None
    )

    repl_module._run_loop(Database(), lambda _gids, _removed: None)
    assert seen_verbs == [
        "create", "read", "update", "delete", "view", "ok", "nah", "work", "undo",
    ]


def test_run_loop_quit_is_recognized(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    inputs = iter(["quit"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(inputs))
    repl_module._run_loop(Database(), lambda _gids, _removed: None)
    out = capsys.readouterr().out
    assert "Goodbye." in out


def test_run_loop_eof_exits_cleanly(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("builtins.input", lambda _prompt="": (_ for _ in ()).throw(EOFError()))
    repl_module._run_loop(Database(), lambda _gids, _removed: None)
    out = capsys.readouterr().out
    assert "Goodbye." in out


def test_run_loop_unknown_command_shows_helpful_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    inputs = iter(["wat", "exit"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(inputs))
    repl_module._run_loop(Database(), lambda _gids, _removed: None)
    out = capsys.readouterr().out
    assert "Unknown command: 'wat'. Type 'help' for available commands." in out


def test_run_loop_view_no_pending_shows_expected_message(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    inputs = iter(["view", "exit"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(inputs))
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


# ---------------------------------------------------------------------------
# Undo parser tests
# ---------------------------------------------------------------------------


def test_parse_undo_assignment_p_then_t() -> None:
    cmd = parse_command("undo", ["p3", "t5"])
    assert isinstance(cmd, UndoAssignmentCommand)
    assert cmd.project_id == 3
    assert cmd.task_id == 5


def test_parse_undo_assignment_t_then_p() -> None:
    cmd = parse_command("undo", ["t5", "p3"])
    assert isinstance(cmd, UndoAssignmentCommand)
    assert cmd.project_id == 3
    assert cmd.task_id == 5


def test_parse_undo_entity_group() -> None:
    cmd = parse_command("undo", ["g1"])
    assert isinstance(cmd, UndoEntityCommand)
    assert cmd.kind == "group"
    assert cmd.entity_id == 1


def test_parse_undo_entity_project() -> None:
    cmd = parse_command("undo", ["p2"])
    assert isinstance(cmd, UndoEntityCommand)
    assert cmd.kind == "project"
    assert cmd.entity_id == 2


def test_parse_undo_entity_task() -> None:
    cmd = parse_command("undo", ["t3"])
    assert isinstance(cmd, UndoEntityCommand)
    assert cmd.kind == "task"
    assert cmd.entity_id == 3


def test_parse_undo_rejects_no_args() -> None:
    with pytest.raises(CommandParseError):
        parse_command("undo", [])


def test_parse_undo_rejects_invalid_tokens() -> None:
    with pytest.raises(CommandParseError):
        parse_command("undo", ["foo"])


def test_parse_undo_rejects_three_args() -> None:
    with pytest.raises(CommandParseError):
        parse_command("undo", ["p1", "t2", "extra"])


# ---------------------------------------------------------------------------
# ok/nah without confirmation
# ---------------------------------------------------------------------------


def test_ok_no_confirmation_resolves_with_comment(monkeypatch: pytest.MonkeyPatch) -> None:
    db = Database()
    g = create_group(db, "Backend")
    p = create_project(db, "api", g.id)
    t = create_task(db, "Task A", None)

    inputs = iter(["looks good"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(inputs))

    execute_command(
        ResolveAssignmentCommand(project_id=p.id, task_id=t.id, status=AssignmentStatus.OK),
        db,
        lambda _gids, _removed: None,
    )

    key = assignment_key(p.id, t.id)
    assert db.assignments[key].status == AssignmentStatus.OK
    assert db.assignments[key].comment == "looks good"


def test_ok_no_confirmation_resolves_without_comment(monkeypatch: pytest.MonkeyPatch) -> None:
    db = Database()
    g = create_group(db, "Backend")
    p = create_project(db, "api", g.id)
    t = create_task(db, "Task A", None)

    inputs = iter([""])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(inputs))

    execute_command(
        ResolveAssignmentCommand(project_id=p.id, task_id=t.id, status=AssignmentStatus.OK),
        db,
        lambda _gids, _removed: None,
    )

    key = assignment_key(p.id, t.id)
    assert db.assignments[key].status == AssignmentStatus.OK
    assert db.assignments[key].comment is None


def test_ok_ctrl_c_during_comment_cancels(monkeypatch: pytest.MonkeyPatch) -> None:
    db = Database()
    g = create_group(db, "Backend")
    p = create_project(db, "api", g.id)
    t = create_task(db, "Task A", None)

    def raise_interrupt(_prompt: str = "") -> str:
        raise KeyboardInterrupt

    monkeypatch.setattr("builtins.input", raise_interrupt)

    execute_command(
        ResolveAssignmentCommand(project_id=p.id, task_id=t.id, status=AssignmentStatus.OK),
        db,
        lambda _gids, _removed: None,
    )

    key = assignment_key(p.id, t.id)
    assert db.assignments[key].status == AssignmentStatus.PENDING


# ---------------------------------------------------------------------------
# Undo command tests
# ---------------------------------------------------------------------------


def test_undo_single_assignment(monkeypatch: pytest.MonkeyPatch) -> None:
    from viber.command_parser import UndoAssignmentCommand
    from viber.service import resolve_assignment

    db = Database()
    g = create_group(db, "Backend")
    p = create_project(db, "api", g.id)
    t = create_task(db, "Task A", None)

    resolve_assignment(db, p.id, t.id, AssignmentStatus.OK, "done")

    execute_command(
        UndoAssignmentCommand(project_id=p.id, task_id=t.id),
        db,
        lambda _gids, _removed: None,
    )

    key = assignment_key(p.id, t.id)
    assert db.assignments[key].status == AssignmentStatus.PENDING
    assert db.assignments[key].comment is None
    assert db.assignments[key].handled_utc is None


def test_undo_already_pending_shows_message(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from viber.command_parser import UndoAssignmentCommand

    db = Database()
    g = create_group(db, "Backend")
    p = create_project(db, "api", g.id)
    t = create_task(db, "Task A", None)

    execute_command(
        UndoAssignmentCommand(project_id=p.id, task_id=t.id),
        db,
        lambda _gids, _removed: None,
    )

    out = capsys.readouterr().out
    assert "already pending" in out


def test_undo_entity_project_with_confirmation(monkeypatch: pytest.MonkeyPatch) -> None:
    from viber.command_parser import UndoEntityCommand
    from viber.service import resolve_assignment

    db = Database()
    g = create_group(db, "Backend")
    p = create_project(db, "api", g.id)
    t1 = create_task(db, "Task A", None)
    t2 = create_task(db, "Task B", None)

    resolve_assignment(db, p.id, t1.id, AssignmentStatus.OK, "done")
    resolve_assignment(db, p.id, t2.id, AssignmentStatus.NAH, "skip")

    inputs = iter(["y"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(inputs))

    execute_command(
        UndoEntityCommand(kind="project", entity_id=p.id),
        db,
        lambda _gids, _removed: None,
    )

    assert db.assignments[assignment_key(p.id, t1.id)].status == AssignmentStatus.PENDING
    assert db.assignments[assignment_key(p.id, t1.id)].comment is None
    assert db.assignments[assignment_key(p.id, t2.id)].status == AssignmentStatus.PENDING
    assert db.assignments[assignment_key(p.id, t2.id)].comment is None


def test_undo_entity_project_cancelled(monkeypatch: pytest.MonkeyPatch) -> None:
    from viber.command_parser import UndoEntityCommand
    from viber.service import resolve_assignment

    db = Database()
    g = create_group(db, "Backend")
    p = create_project(db, "api", g.id)
    t = create_task(db, "Task A", None)

    resolve_assignment(db, p.id, t.id, AssignmentStatus.OK, "done")

    inputs = iter(["n"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(inputs))

    execute_command(
        UndoEntityCommand(kind="project", entity_id=p.id),
        db,
        lambda _gids, _removed: None,
    )

    assert db.assignments[assignment_key(p.id, t.id)].status == AssignmentStatus.OK


def test_undo_entity_task_with_confirmation(monkeypatch: pytest.MonkeyPatch) -> None:
    from viber.command_parser import UndoEntityCommand
    from viber.service import resolve_assignment

    db = Database()
    g = create_group(db, "Backend")
    p1 = create_project(db, "api", g.id)
    p2 = create_project(db, "auth", g.id)
    t = create_task(db, "Task A", None)

    resolve_assignment(db, p1.id, t.id, AssignmentStatus.OK, "done")
    resolve_assignment(db, p2.id, t.id, AssignmentStatus.NAH, None)

    inputs = iter(["y"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(inputs))

    execute_command(
        UndoEntityCommand(kind="task", entity_id=t.id),
        db,
        lambda _gids, _removed: None,
    )

    assert db.assignments[assignment_key(p1.id, t.id)].status == AssignmentStatus.PENDING
    assert db.assignments[assignment_key(p2.id, t.id)].status == AssignmentStatus.PENDING


def test_undo_entity_group_with_confirmation(monkeypatch: pytest.MonkeyPatch) -> None:
    from viber.command_parser import UndoEntityCommand
    from viber.service import resolve_assignment

    db = Database()
    g = create_group(db, "Backend")
    p = create_project(db, "api", g.id)
    t = create_task(db, "Task A", None)

    resolve_assignment(db, p.id, t.id, AssignmentStatus.OK, "done")

    inputs = iter(["y"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(inputs))

    execute_command(
        UndoEntityCommand(kind="group", entity_id=g.id),
        db,
        lambda _gids, _removed: None,
    )

    assert db.assignments[assignment_key(p.id, t.id)].status == AssignmentStatus.PENDING


def test_undo_entity_no_resolved_shows_message(
    capsys: pytest.CaptureFixture[str],
) -> None:
    from viber.command_parser import UndoEntityCommand

    db = Database()
    g = create_group(db, "Backend")
    p = create_project(db, "api", g.id)
    create_task(db, "Task A", None)

    execute_command(
        UndoEntityCommand(kind="project", entity_id=p.id),
        db,
        lambda _gids, _removed: None,
    )

    out = capsys.readouterr().out
    assert "No resolved assignments" in out


# ---------------------------------------------------------------------------
# Alias mapping (covered by updated test_run_loop_aliases_are_mapped_to_full_verbs above)
# ---------------------------------------------------------------------------


def test_run_repl_without_check_path_only_saves_after_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = Database()
    data_path = Path("/tmp/viber-data.json")
    events: list[str] = []

    def fake_run_loop(_db: Database, after_mutation: repl_module.MutationHook) -> None:
        after_mutation({1}, None)

    def fake_save_database(saved_db: Database, saved_path: Path) -> None:
        assert saved_db is db
        assert saved_path == data_path
        events.append("save")

    monkeypatch.setattr(repl_module, "_run_loop", fake_run_loop)
    monkeypatch.setattr(repl_module, "save_database", fake_save_database)
    monkeypatch.setattr(
        repl_module,
        "render_check_pages",
        lambda *_args, **_kwargs: events.append("render"),
    )
    monkeypatch.setattr(
        repl_module,
        "remove_check_page",
        lambda *_args, **_kwargs: events.append("remove"),
    )

    repl_module.run_repl(db, data_path, None)

    assert events == ["save"]


def test_run_repl_removes_deleted_group_pages_before_full_refresh(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = Database()
    data_path = Path("/tmp/viber-data.json")
    check_path = Path("/tmp/viber-check.html")
    events: list[str] = []

    def fake_run_loop(_db: Database, after_mutation: repl_module.MutationHook) -> None:
        after_mutation(None, {"Frontend", "Backend"})

    def fake_save_database(saved_db: Database, saved_path: Path) -> None:
        assert saved_db is db
        assert saved_path == data_path
        events.append("save")

    def fake_remove_check_page(removed_path: Path, group_name: str) -> None:
        assert removed_path == check_path
        events.append(f"remove:{group_name}")

    def fake_render_check_pages(
        rendered_db: Database,
        rendered_path: Path,
        affected_group_ids: set[int] | None = None,
    ) -> None:
        assert rendered_db is db
        assert rendered_path == check_path
        assert affected_group_ids is None
        events.append("render:all")

    monkeypatch.setattr(repl_module, "_run_loop", fake_run_loop)
    monkeypatch.setattr(repl_module, "save_database", fake_save_database)
    monkeypatch.setattr(repl_module, "remove_check_page", fake_remove_check_page)
    monkeypatch.setattr(repl_module, "render_check_pages", fake_render_check_pages)

    repl_module.run_repl(db, data_path, check_path)

    assert events == ["save", "remove:Backend", "remove:Frontend", "render:all"]


def test_run_repl_renders_only_affected_groups_after_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = Database()
    data_path = Path("/tmp/viber-data.json")
    check_path = Path("/tmp/viber-check.html")
    events: list[str] = []

    def fake_run_loop(_db: Database, after_mutation: repl_module.MutationHook) -> None:
        after_mutation({3, 1}, None)

    def fake_save_database(saved_db: Database, saved_path: Path) -> None:
        assert saved_db is db
        assert saved_path == data_path
        events.append("save")

    def fake_render_check_pages(
        rendered_db: Database,
        rendered_path: Path,
        affected_group_ids: set[int] | None = None,
    ) -> None:
        assert rendered_db is db
        assert rendered_path == check_path
        assert affected_group_ids == {1, 3}
        events.append("render:affected")

    monkeypatch.setattr(repl_module, "_run_loop", fake_run_loop)
    monkeypatch.setattr(repl_module, "save_database", fake_save_database)
    monkeypatch.setattr(
        repl_module,
        "remove_check_page",
        lambda *_args, **_kwargs: events.append("remove"),
    )
    monkeypatch.setattr(repl_module, "render_check_pages", fake_render_check_pages)

    repl_module.run_repl(db, data_path, check_path)

    assert events == ["save", "render:affected"]
