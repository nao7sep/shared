"""Tests for repl module."""

import pytest
from tk.repl import parse_command, _try_parse_first_num_arg


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

    def test_parse_command_with_flags(self):
        """Test parsing command with flags."""
        cmd, args, kwargs = parse_command("done 1 --note finished --date 2026-02-09")

        assert cmd == "done"
        assert args == ["1"]
        assert kwargs == {"note": "finished", "date": "2026-02-09"}

    def test_parse_command_flag_int_value(self):
        """Test that integer flag values are converted."""
        cmd, args, kwargs = parse_command("history --days 7")

        assert cmd == "history"
        assert kwargs["days"] == 7

    def test_parse_command_flag_boolean(self):
        """Test boolean flags."""
        cmd, args, kwargs = parse_command("sync --force")

        assert cmd == "sync"
        assert kwargs["force"] is True

    def test_parse_command_no_flag_commands(self):
        """Test that add/edit/note don't parse flags."""
        # 'add' command should treat --note as part of text
        cmd, args, kwargs = parse_command("add task with --note text")

        assert cmd == "add"
        assert args == ["task", "with", "--note", "text"]
        assert kwargs == {}

    def test_parse_command_edit_no_flags(self):
        """Test that edit command doesn't parse flags."""
        cmd, args, kwargs = parse_command("edit 1 new --text here")

        assert cmd == "edit"
        assert args == ["1", "new", "--text", "here"]
        assert kwargs == {}

    def test_parse_command_multiple_args_and_flags(self):
        """Test parsing mix of args and flags."""
        # Note: The parser takes the next non-flag word as the value
        # So "test note" becomes two args: "test" is value for --note, "note" is a standalone arg
        cmd, args, kwargs = parse_command("done 1 --note completed --date 2026-02-09")

        assert cmd == "done"
        assert args == ["1"]
        assert kwargs["note"] == "completed"
        assert kwargs["date"] == "2026-02-09"


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
