"""REPL parsing and loop orchestration for tk."""

import os
import shlex
import traceback
from typing import Any

from tk import commands, dispatcher, markdown, prompts
from tk.errors import AppError, UsageError
from tk.models import TaskStatus
from tk.session import Session

_NO_FLAG_COMMANDS = frozenset(
    (
        "add",
        "a",
        "edit",
        "e",
        "note",
        "n",
        "done",
        "d",
        "cancel",
        "c",
    )
)
_HANDLED_COMMAND_TO_STATUS = {
    "done": TaskStatus.DONE,
    "cancel": TaskStatus.CANCELLED,
}


def _report_unexpected_error(error: Exception) -> None:
    """Print an unexpected exception with optional debug traceback."""
    print(f"ERROR: {error}")
    if os.getenv("TK_DEBUG"):
        print("Debug traceback:")
        traceback.print_exc()


def _sync_on_exit(session: Session) -> None:
    """Run exit-time markdown sync behind the REPL error boundary."""
    prof = session.profile
    tasks_data = session.tasks
    if not prof or not tasks_data or not prof.sync_on_exit:
        return

    try:
        markdown.generate_todo(tasks_data.tasks, prof.output_path)
    except AppError as e:
        print(f"ERROR: {e}")
    except Exception as e:
        _report_unexpected_error(e)


def parse_command(line: str) -> tuple[str, list[Any], dict[str, Any]]:
    """Parse command line into (command, args, kwargs)."""
    try:
        lexer = shlex.shlex(line, posix=True)
        lexer.whitespace_split = True
        lexer.commenters = ""
        lexer.quotes = '"'
        parts = list(lexer)
    except ValueError as e:
        raise UsageError(f"Invalid command syntax: {e}") from e

    if not parts:
        return "", [], {}

    cmd = parts[0]

    if cmd in _NO_FLAG_COMMANDS:
        return cmd, parts[1:], {}

    args = []
    kwargs = {}

    i = 1
    while i < len(parts):
        part = parts[i]

        if part.startswith("--"):
            flag_name = part[2:].replace("-", "_")

            if i + 1 < len(parts) and not parts[i + 1].startswith("--"):
                value: Any = parts[i + 1]
                try:
                    value = int(value)
                except ValueError:
                    pass

                kwargs[flag_name] = value
                i += 2
            else:
                kwargs[flag_name] = True
                i += 1
        else:
            args.append(part)
            i += 1

    return cmd, args, kwargs


def _try_parse_first_num_arg(args: list[Any]) -> int | None:
    """Parse first arg as int if possible; return None if missing/invalid."""
    if not args:
        return None

    try:
        return int(args[0])
    except (TypeError, ValueError):
        return None


def _prepare_interactive_command(
    cmd: str,
    args: list[Any],
    kwargs: dict[str, Any],
    session: Session,
) -> tuple[str, list[Any], dict[str, Any]] | str:
    """Collect interactive inputs for commands that need REPL prompts."""
    normalized = dispatcher.resolve_command_alias(cmd)

    if normalized in _HANDLED_COMMAND_TO_STATUS:
        if kwargs or len(args) != 1:
            return cmd, args, kwargs

        num = _try_parse_first_num_arg(args)
        if num is None:
            return cmd, args, kwargs

        task = session.get_task_by_display_number(num)
        status = _HANDLED_COMMAND_TO_STATUS[normalized]
        default_date = commands.get_default_subjective_date(session)

        try:
            result = prompts.collect_done_cancel_prompts(
                task=task,
                status=status,
                default_date=default_date,
            )

            if result == "CANCELLED":
                session.clear_last_list()
                return "[Operation Cancelled]"

            array_index = session.resolve_array_index(num)
            cmd_fn = commands.cmd_done if normalized == "done" else commands.cmd_cancel
            outcome = cmd_fn(session, array_index, result.note, result.date)
            session.clear_last_list()
            return outcome

        except KeyboardInterrupt:
            print()
            session.clear_last_list()
            return "[Operation Cancelled]"

    elif normalized == "delete":
        if kwargs or len(args) != 1:
            return cmd, args, kwargs

        num = _try_parse_first_num_arg(args)
        if num is None:
            return cmd, args, kwargs

        task = session.get_task_by_display_number(num)
        kwargs["confirm"] = prompts.collect_delete_confirmation(task)

    return cmd, args, kwargs


def repl(session: Session) -> None:
    """Run the REPL loop."""
    print()
    print("Type 'exit' or 'quit' to exit, or Ctrl-D")

    while True:
        print()
        try:
            line = input("> ")

            if not line.strip():
                continue

            cmd, args, kwargs = parse_command(line)
            if not cmd:
                continue

            prepared = _prepare_interactive_command(cmd, args, kwargs, session)
            if isinstance(prepared, str):
                print(prepared)
                continue

            cmd, args, kwargs = prepared
            result = dispatcher.execute_command(cmd, args, kwargs, session)

            if result == "EXIT":
                print("Exiting.")
                break

            print(result)

        except EOFError:
            print()
            break

        except KeyboardInterrupt:
            print()
            continue

        except AppError as e:
            # Expected business logic errors (user errors, validation failures)
            print(f"ERROR: {e}")

        except Exception as e:
            # Unexpected errors - provide more detail in debug mode
            _report_unexpected_error(e)

    _sync_on_exit(session)
