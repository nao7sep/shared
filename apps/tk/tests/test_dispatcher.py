"""Tests for dispatcher module."""

import pytest
from tk import dispatcher


class TestCommandAliases:
    """Test command alias resolution."""

    def test_resolve_alias_a(self):
        """Test that 'a' resolves to 'add'."""
        assert dispatcher.resolve_command_alias("a") == "add"

    def test_resolve_alias_l(self):
        """Test that 'l' resolves to 'list'."""
        assert dispatcher.resolve_command_alias("l") == "list"

    def test_resolve_alias_d(self):
        """Test that 'd' resolves to 'done'."""
        assert dispatcher.resolve_command_alias("d") == "done"

    def test_resolve_alias_all(self):
        """Test all aliases."""
        aliases = {
            "a": "add",
            "l": "list",
            "h": "history",
            "d": "done",
            "c": "cancel",
            "e": "edit",
            "n": "note",
            "s": "sync",
            "t": "today",
            "y": "yesterday",
            "r": "recent",
        }

        for alias, full_name in aliases.items():
            assert dispatcher.resolve_command_alias(alias) == full_name

    def test_resolve_unknown_unchanged(self):
        """Test that unknown commands pass through unchanged."""
        assert dispatcher.resolve_command_alias("unknown") == "unknown"
        assert dispatcher.resolve_command_alias("list") == "list"


class TestNormalizeArgs:
    """Test argument normalization."""

    def test_normalize_args_add(self):
        """Test that add command joins multiple args."""
        result = dispatcher._normalize_args("add", ["word1", "word2", "word3"])

        assert result == ["word1 word2 word3"]

    def test_normalize_args_edit_converts_int(self):
        """Test that edit command converts first arg to int."""
        result = dispatcher._normalize_args("edit", ["1", "new", "text"])

        assert result[0] == 1
        assert result[1] == "new"
        assert result[2] == "text"

    def test_normalize_args_done_converts_int(self):
        """Test that done command converts first arg to int."""
        result = dispatcher._normalize_args("done", ["2"])

        assert result == [2]

    def test_normalize_args_invalid_int(self):
        """Test that non-int strings are left unchanged."""
        result = dispatcher._normalize_args("done", ["abc"])

        assert result == ["abc"]

    def test_normalize_args_passthrough(self):
        """Test that other commands pass through unchanged."""
        result = dispatcher._normalize_args("list", ["arg1", "arg2"])

        assert result == ["arg1", "arg2"]


class TestCommandRegistry:
    """Test command registry structure."""

    def test_registry_has_all_commands(self):
        """Test that all expected commands are registered."""
        expected_commands = [
            "add", "list", "history",
            "done", "cancel", "edit", "delete",
            "note", "date", "sync",
            "today", "yesterday", "recent", "help",
        ]

        for cmd in expected_commands:
            assert cmd in dispatcher.COMMAND_REGISTRY

    def test_registry_handlers_have_executor(self):
        """Test that all handlers have executor function."""
        for cmd, handler in dispatcher.COMMAND_REGISTRY.items():
            assert hasattr(handler, "executor")
            assert callable(handler.executor)

    def test_registry_handlers_have_usage(self):
        """Test that all handlers have usage string."""
        for cmd, handler in dispatcher.COMMAND_REGISTRY.items():
            assert hasattr(handler, "usage")
            assert isinstance(handler.usage, str)
            assert hasattr(handler, "summary")
            assert isinstance(handler.summary, str)

    def test_list_commands_dont_clear_list(self):
        """Test that list commands preserve mapping."""
        list_commands = ["list", "history", "today", "yesterday", "recent"]

        for cmd in list_commands:
            handler = dispatcher.COMMAND_REGISTRY[cmd]
            assert handler.clears_list is False

    def test_mutation_commands_clear_list(self):
        """Test that mutation commands clear mapping."""
        mutation_commands = ["add", "done", "cancel", "edit", "delete", "note", "date", "sync"]

        for cmd in mutation_commands:
            handler = dispatcher.COMMAND_REGISTRY[cmd]
            assert handler.clears_list is True


class TestExecuteCommand:
    """Test execute_command function."""

    def test_execute_command_add(self, sample_session):
        """Test executing add command."""
        result = dispatcher.execute_command("add", ["Test task"], {}, sample_session)

        assert result == "Task added."

    def test_execute_command_list(self, sample_session):
        """Test executing list command."""
        result = dispatcher.execute_command("list", [], {}, sample_session)

        assert "Task one" in result

    def test_execute_command_done(self, sample_session):
        """Test executing done command."""
        # Set up mapping first
        sample_session.set_last_list([(1, 0)])

        result = dispatcher.execute_command("done", [1], {}, sample_session)

        assert "marked as done" in result

    def test_execute_command_done_non_numeric_usage_error(self, sample_session):
        """Test that done command requires numeric task number."""
        with pytest.raises(ValueError, match="Usage: done <num>"):
            dispatcher.execute_command("done", ["abc"], {}, sample_session)

    def test_history_rejects_unknown_flag(self, sample_session):
        """Test that history rejects unrecognised flags."""
        with pytest.raises(ValueError, match="Unknown flags: --bad-flag"):
            dispatcher.execute_command("history", [], {"bad_flag": 1}, sample_session)

    def test_delete_rejects_unknown_flag(self, sample_session):
        """Test that delete rejects unrecognised flags."""
        sample_session.set_last_list([(1, 0)])
        with pytest.raises(ValueError, match="Unknown flags: --unknown"):
            dispatcher.execute_command("delete", [1], {"unknown": True}, sample_session)

    def test_date_rejects_unknown_flag(self, sample_session):
        """Test that date rejects any flags."""
        sample_session.set_last_list([(1, 0)])
        with pytest.raises(ValueError, match="Unknown flags: --force"):
            dispatcher.execute_command("date", [1, "2026-03-01"], {"force": True}, sample_session)

    def test_execute_command_unknown(self, sample_session):
        """Test that unknown command raises ValueError."""
        with pytest.raises(ValueError, match="Unknown command"):
            dispatcher.execute_command("unknown", [], {}, sample_session)

    def test_execute_command_exit(self, sample_session):
        """Test that exit returns EXIT."""
        result = dispatcher.execute_command("exit", [], {}, sample_session)

        assert result == "EXIT"

    def test_execute_command_quit(self, sample_session):
        """Test that quit returns EXIT."""
        result = dispatcher.execute_command("quit", [], {}, sample_session)

        assert result == "EXIT"

    def test_execute_command_clears_list(self, sample_session):
        """Test that commands clear list mapping after mutation."""
        # Set up mapping
        sample_session.set_last_list([(1, 0), (2, 1)])

        # Execute mutation command
        dispatcher.execute_command("add", ["New task"], {}, sample_session)

        # Mapping should be cleared
        assert sample_session.last_list == []

    def test_execute_command_list_preserves_mapping(self, sample_session):
        """Test that list command updates but doesn't clear mapping."""
        # Execute list command
        dispatcher.execute_command("list", [], {}, sample_session)

        # Mapping should be set (not cleared)
        assert len(sample_session.last_list) > 0


class TestHelpRendering:
    """Test metadata-driven help rendering."""

    def test_help_text_includes_all_registry_commands(self):
        help_text = dispatcher.render_help_text()

        for cmd in dispatcher.COMMAND_REGISTRY:
            display_usage = next(
                row.display_usage
                for row in dispatcher.command_doc_entries()
                if row.command == cmd
            )
            assert display_usage in help_text

    def test_help_text_includes_footer(self):
        help_text = dispatcher.render_help_text()
        assert "For full documentation, see README.md" in help_text
