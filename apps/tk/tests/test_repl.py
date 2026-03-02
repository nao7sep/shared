"""Tests for repl module."""

import pytest

from tk.errors import AppError, UsageError
from tk.models import DoneCancelResult, Task, TaskListItem
from tk.repl import parse_command, _try_parse_first_num_arg
import tk.repl as repl_module


def _make_item(display_num: int, array_index: int, task: Task | None = None) -> TaskListItem:
    """Helper to create a TaskListItem for tests."""
    if task is None:
        task = Task(text="dummy", status="pending", created_utc="2026-01-01T00:00:00+00:00")
    return TaskListItem(array_index=array_index, task=task, display_num=display_num)


class TestParseCommand:
    """Test parse_command function."""

    def test_parse_command_empty(self):
        """Test parsing empty input."""
        cmd, args, kwargs = parse_command("")

        assert cmd == ""
        assert args == []
        assert kwargs == {}

    def test_parse_command_simple(self):
        """Test parsing simple command."""
        cmd, args, kwargs = parse_command("add task text")

        assert cmd == "add"
        assert args == ["task", "text"]
        assert kwargs == {}

    def test_parse_command_apostrophe_in_text(self):
        """Test that apostrophes in task text are handled without error."""
        cmd, args, kwargs = parse_command("add do something about python's something")

        assert cmd == "add"
        assert args == ["do", "something", "about", "python's", "something"]
        assert kwargs == {}

    def test_parse_command_supports_quoted_text(self):
        """Test that quoted task text is parsed like a shell command line."""
        cmd, args, kwargs = parse_command('add "task with spaces"')

        assert cmd == "add"
        assert args == ["task with spaces"]
        assert kwargs == {}

    def test_parse_command_invalid_quotes_raise_usage_error(self):
        """Test that malformed quoted input returns a user-facing syntax error."""
        with pytest.raises(UsageError, match="Invalid command syntax"):
            parse_command('add "unterminated')

    def test_parse_command_flag_int_value(self):
        """Test that integer flag values are converted."""
        cmd, args, kwargs = parse_command("history --days 7")

        assert cmd == "history"
        assert kwargs["days"] == 7

    def test_parse_command_flag_hyphen_to_underscore(self):
        """Test that hyphenated flags are normalized to underscore keys."""
        cmd, args, kwargs = parse_command("history --working-days 3")

        assert cmd == "history"
        assert kwargs["working_days"] == 3

    def test_parse_command_flag_boolean(self):
        """Test boolean flags."""
        cmd, args, kwargs = parse_command("sync --force")

        assert cmd == "sync"
        assert kwargs["force"] is True

    def test_parse_command_no_flag_commands(self):
        """Test that add/edit/note/done/cancel treat all words as plain args."""
        cmd, args, kwargs = parse_command("add task with extra words")

        assert cmd == "add"
        assert args == ["task", "with", "extra", "words"]
        assert kwargs == {}

    def test_parse_command_edit_no_flags(self):
        """Test that edit command doesn't parse flags."""
        cmd, args, kwargs = parse_command("edit 1 new --text here")

        assert cmd == "edit"
        assert args == ["1", "new", "--text", "here"]
        assert kwargs == {}

    @pytest.mark.parametrize(
        ("line", "expected_cmd", "expected_args"),
        [
            ('add "task with spaces" --literal tail', "add", ["task with spaces", "--literal", "tail"]),
            ('edit 1 "new text" --literal tail', "edit", ["1", "new text", "--literal", "tail"]),
            ('note 2 "note text" --literal tail', "note", ["2", "note text", "--literal", "tail"]),
        ],
    )
    def test_parse_command_text_commands_preserve_rest_of_line(self, line, expected_cmd, expected_args):
        """Test that text commands keep the rest of the line as plain arguments."""
        cmd, args, kwargs = parse_command(line)

        assert cmd == expected_cmd
        assert args == expected_args
        assert kwargs == {}


class TestTryParseFirstNumArg:
    """Test _try_parse_first_num_arg function."""

    def test_parse_first_num_arg_valid(self):
        """Test parsing valid integer."""
        result = _try_parse_first_num_arg([1, "other", "args"])

        assert result == 1

    def test_parse_first_num_arg_string_int(self):
        """Test parsing string that can be int."""
        result = _try_parse_first_num_arg(["123", "other"])

        assert result == 123

    def test_parse_first_num_arg_invalid(self):
        """Test parsing invalid string returns None."""
        result = _try_parse_first_num_arg(["abc", "other"])

        assert result is None

    def test_parse_first_num_arg_empty(self):
        """Test parsing empty list returns None."""
        result = _try_parse_first_num_arg([])

        assert result is None

    def test_parse_first_num_arg_none(self):
        """Test parsing None in list returns None."""
        result = _try_parse_first_num_arg([None])

        assert result is None


class TestPrepareInteractiveCommand:
    """Test interactive REPL command preparation."""

    def test_done_command_executes_prompted_action(self, sample_session, monkeypatch):
        """Test that done uses prompt results and clears the list mapping."""
        sample_session.set_last_list([_make_item(1, 0, sample_session.tasks.tasks[0])])
        captured: dict[str, object] = {}

        monkeypatch.setattr(repl_module.commands, "get_default_subjective_date", lambda session: "2026-02-09")
        monkeypatch.setattr(
            repl_module.prompts,
            "collect_done_cancel_prompts",
            lambda **kwargs: DoneCancelResult(note="Finished", date="2026-02-08"),
        )

        def fake_cmd_done(session, array_index, note, date_str):
            captured["call"] = (session, array_index, note, date_str)
            return "Task marked as done."

        monkeypatch.setattr(repl_module.commands, "cmd_done", fake_cmd_done)

        result = repl_module._prepare_interactive_command("done", ["1"], {}, sample_session)

        assert result == "Task marked as done."
        assert captured["call"] == (sample_session, 0, "Finished", "2026-02-08")
        assert sample_session.last_list == []

    def test_cancelled_prompt_result_clears_mapping(self, sample_session, monkeypatch):
        """Test that cancelled interactive flow clears mapping and returns marker text."""
        sample_session.set_last_list([_make_item(1, 0, sample_session.tasks.tasks[0])])

        monkeypatch.setattr(repl_module.commands, "get_default_subjective_date", lambda session: "2026-02-09")
        monkeypatch.setattr(
            repl_module.prompts,
            "collect_done_cancel_prompts",
            lambda **kwargs: "CANCELLED",
        )

        result = repl_module._prepare_interactive_command("done", ["1"], {}, sample_session)

        assert result == "[Operation Cancelled]"
        assert sample_session.last_list == []

    def test_delete_prompt_is_skipped_for_invalid_usage(self, sample_session, monkeypatch):
        """Test that invalid delete syntax does not trigger a confirmation prompt."""
        sample_session.set_last_list([_make_item(1, 0, sample_session.tasks.tasks[0])])

        def fail_if_called(task):
            raise AssertionError("delete confirmation should not run for invalid usage")

        monkeypatch.setattr(repl_module.prompts, "collect_delete_confirmation", fail_if_called)

        result = repl_module._prepare_interactive_command("delete", ["1", "extra"], {}, sample_session)

        assert result == ("delete", ["1", "extra"], {})

    def test_delete_prompt_sets_confirm_flag(self, sample_session, monkeypatch):
        """Test that valid delete syntax collects confirmation."""
        sample_session.set_last_list([_make_item(1, 0, sample_session.tasks.tasks[0])])

        monkeypatch.setattr(
            repl_module.prompts,
            "collect_delete_confirmation",
            lambda task: True,
        )

        cmd, args, kwargs = repl_module._prepare_interactive_command("delete", ["1"], {}, sample_session)

        assert (cmd, args) == ("delete", ["1"])
        assert kwargs == {"confirm": True}


class TestReplLoop:
    """Test the REPL loop behavior."""

    def test_repl_handles_app_error_and_continues(self, sample_session, monkeypatch, capsys):
        """Test that business errors are shown and the loop continues."""
        inputs = iter(["list", "exit"])
        results = iter([AppError("Bad command"), "EXIT"])

        monkeypatch.setattr("builtins.input", lambda _: next(inputs))

        def fake_execute(cmd, args, kwargs, session):
            result = next(results)
            if isinstance(result, Exception):
                raise result
            return result

        monkeypatch.setattr(repl_module.dispatcher, "execute_command", fake_execute)

        repl_module.repl(sample_session)

        output = capsys.readouterr().out
        assert "ERROR: Bad command" in output
        assert "Exiting." in output

    def test_repl_reports_invalid_command_syntax(self, sample_session, monkeypatch, capsys):
        """Test that malformed quoted input is shown as a usage error."""
        inputs = iter(['add "unterminated', "exit"])

        monkeypatch.setattr("builtins.input", lambda _: next(inputs))

        repl_module.repl(sample_session)

        output = capsys.readouterr().out
        assert "ERROR: Invalid command syntax" in output
        assert "Exiting." in output

    def test_repl_syncs_on_exit_when_enabled(self, sample_session, monkeypatch):
        """Test that sync_on_exit regenerates TODO.md after leaving the loop."""
        sample_session.profile.sync_on_exit = True
        inputs = iter(["exit"])
        captured: dict[str, object] = {}

        monkeypatch.setattr("builtins.input", lambda _: next(inputs))

        def fake_generate_todo(tasks, output_path):
            captured["call"] = (tasks, output_path)

        monkeypatch.setattr(repl_module.markdown, "generate_todo", fake_generate_todo)

        repl_module.repl(sample_session)

        assert captured["call"] == (
            sample_session.tasks.tasks,
            sample_session.profile.output_path,
        )

    def test_repl_reports_sync_on_exit_failure(self, sample_session, monkeypatch, capsys):
        """Test that exit-sync errors are shown instead of escaping."""
        sample_session.profile.sync_on_exit = True
        inputs = iter(["exit"])

        monkeypatch.setattr("builtins.input", lambda _: next(inputs))
        monkeypatch.setattr(
            repl_module.markdown,
            "generate_todo",
            lambda tasks, output_path: (_ for _ in ()).throw(OSError("disk full")),
        )

        repl_module.repl(sample_session)

        output = capsys.readouterr().out
        assert "Exiting." in output
        assert "ERROR: disk full" in output
