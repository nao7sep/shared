"""Tests for repl module."""

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

    def test_parse_command_apostrophe_in_text(self):
        """Test that apostrophes in task text are handled without error."""
        cmd, args, kwargs = parse_command("add do something about python's something")

        assert cmd == "add"
        assert args == ["do", "something", "about", "python's", "something"]
        assert kwargs == {}

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
