"""REPL parsing and loop orchestration for tk."""

from typing import Any

from tk import commands, dispatcher, markdown
from tk.session import Session
from tk.validation import validate_date_format


def parse_command(line: str) -> tuple[str, list[Any], dict[str, Any]]:
    """Parse command line into (command, args, kwargs)."""
    parts = line.split()

    if not parts:
        return "", [], {}

    cmd = parts[0]

    no_flag_commands = {
        "add", "a",
        "edit", "e",
        "note", "n",
    }

    if cmd in no_flag_commands:
        return cmd, parts[1:], {}

    args = []
    kwargs = {}

    i = 1
    while i < len(parts):
        part = parts[i]

        if part.startswith("--"):
            flag_name = part[2:]

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

    if normalized in ("done", "cancel"):
        num = _try_parse_first_num_arg(args)
        if num is None:
            return cmd, args, kwargs

        task = session.get_task_by_display_number(num)
        status = "done" if normalized == "done" else "cancelled"

        provided_date = kwargs.get("date")
        default_date = provided_date if provided_date else commands.get_default_subjective_date(session)

        print(f"Task: {task['text']}")
        print(f"Will be marked as: {status}")
        print(f"Subjective date: {default_date}")
        print("(Press Ctrl+C to cancel)")

        try:
            if "note" not in kwargs:
                note_input = input("Note (press Enter to skip): ").strip()
                kwargs["note"] = note_input if note_input else None

            if "date" not in kwargs:
                date_input = input(f"Date override (press Enter to use {default_date}): ").strip()
                if date_input:
                    validate_date_format(date_input)
                    kwargs["date"] = date_input
                else:
                    kwargs["date"] = default_date

        except KeyboardInterrupt:
            print()
            session.clear_last_list()
            return "Cancelled."

    elif normalized == "delete":
        num = _try_parse_first_num_arg(args)
        if num is None:
            return cmd, args, kwargs

        task = session.get_task_by_display_number(num)
        print(f"Task: {task['text']}")
        print(f"Status: {task['status']}")

        confirm = input("Delete permanently? (yes/N): ").strip().lower()
        kwargs["confirm"] = confirm == "yes"

    return cmd, args, kwargs


def repl(session: Session) -> None:
    """Run the REPL loop."""
    try:
        import readline
    except ImportError:
        pass

    print("tk task manager")
    print("Type 'exit' or 'quit' to exit, or Ctrl-D")
    print()

    while True:
        try:
            line = input("tk> ")

            if not line.strip():
                continue

            cmd, args, kwargs = parse_command(line)
            if not cmd:
                continue

            prepared = _prepare_interactive_command(cmd, args, kwargs, session)
            if isinstance(prepared, str):
                print(prepared)
                print()
                continue

            cmd, args, kwargs = prepared
            result = dispatcher.execute_command(cmd, args, kwargs, session)

            if result == "EXIT":
                break

            print(result)
            print()

        except EOFError:
            print()
            break

        except KeyboardInterrupt:
            print()
            continue

        except Exception as e:
            print(f"Error: {e}")

    profile_data = session.profile
    tasks_data = session.tasks
    if profile_data and tasks_data and profile_data.get("sync_on_exit", False):
        markdown.generate_todo(tasks_data["tasks"], profile_data["output_path"])

    if tasks_data:
        tasks = tasks_data["tasks"]
        pending_count = sum(1 for t in tasks if t["status"] == "pending")
        done_count = sum(1 for t in tasks if t["status"] == "done")
        cancelled_count = sum(1 for t in tasks if t["status"] == "cancelled")

        print(f"{pending_count} pending, {done_count} done, {cancelled_count} cancelled")

    print()
