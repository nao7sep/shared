"""CLI REPL interface for tk."""

import sys
import argparse
from typing import Any
import shlex

from tk import profile, data, commands


def parse_command(line: str) -> tuple[str, list[Any], dict[str, Any]]:
    """Parse command line into (command, args, kwargs).

    Args:
        line: Command line input

    Returns:
        Tuple of (command, args, kwargs)

    Examples:
        "add foo bar" → ("add", ["foo bar"], {})
        "done 1 --note 'finished'" → ("done", [1], {"note": "finished"})
        "history --days 7" → ("history", [], {"days": 7})
        "edit 1 new text here" → ("edit", [1, "new text here"], {})
    """
    # Use shlex to handle quoted strings properly
    try:
        parts = shlex.split(line)
    except ValueError as e:
        raise ValueError(f"Parse error: {e}")

    if not parts:
        return "", [], {}

    cmd = parts[0]
    args = []
    kwargs = {}

    i = 1
    while i < len(parts):
        part = parts[i]

        if part.startswith("--"):
            # This is a flag
            flag_name = part[2:]

            # Check if next part is the value
            if i + 1 < len(parts) and not parts[i + 1].startswith("--"):
                # Has a value
                value = parts[i + 1]

                # Try to parse as int
                try:
                    value = int(value)
                except ValueError:
                    pass  # Keep as string

                kwargs[flag_name] = value
                i += 2
            else:
                # Boolean flag
                kwargs[flag_name] = True
                i += 1
        else:
            args.append(part)
            i += 1

    # Special handling for certain commands
    if cmd == "add":
        # Join all args into single text
        if args:
            args = [" ".join(str(a) for a in args)]

    elif cmd == "edit":
        # First arg is number, rest is text
        if len(args) >= 2:
            try:
                num = int(args[0])
                text = " ".join(str(a) for a in args[1:])
                args = [num, text]
            except ValueError:
                pass  # Let command handler deal with it

    elif cmd in ("done", "decline"):
        # First arg should be int
        if args:
            try:
                args[0] = int(args[0])
            except ValueError:
                pass

    elif cmd == "delete":
        # Arg should be int
        if args:
            try:
                args[0] = int(args[0])
            except ValueError:
                pass

    return cmd, args, kwargs


def execute_command(cmd: str, args: list[Any], kwargs: dict[str, Any], session: dict[str, Any]) -> str:
    """Execute a command.

    Args:
        cmd: Command name
        args: Positional arguments
        kwargs: Keyword arguments
        session: Current session state

    Returns:
        Result message

    Raises:
        ValueError: If command is invalid or arguments are wrong
    """
    if cmd == "new":
        if len(args) != 1:
            raise ValueError("Usage: new <profile_path>")
        return commands.cmd_new(args[0], session)

    elif cmd == "add":
        if len(args) != 1:
            raise ValueError("Usage: add <text>")
        return commands.cmd_add(session, args[0])

    elif cmd == "list":
        if args or kwargs:
            raise ValueError("Usage: list")
        return commands.cmd_list(session)

    elif cmd == "history":
        days = kwargs.get("days")
        if args:
            raise ValueError("Usage: history [--days N]")
        return commands.cmd_history(session, days)

    elif cmd == "done":
        if len(args) != 1:
            raise ValueError("Usage: done <num> [--note <text>] [--date YYYY-MM-DD]")
        note = kwargs.get("note")
        date_str = kwargs.get("date")
        return commands.cmd_done(session, args[0], note, date_str)

    elif cmd == "decline":
        if len(args) != 1:
            raise ValueError("Usage: decline <num> [--note <text>] [--date YYYY-MM-DD]")
        note = kwargs.get("note")
        date_str = kwargs.get("date")
        return commands.cmd_decline(session, args[0], note, date_str)

    elif cmd == "edit":
        if len(args) != 2:
            raise ValueError("Usage: edit <num> <text>")
        return commands.cmd_edit(session, args[0], args[1])

    elif cmd == "delete":
        if len(args) != 1:
            raise ValueError("Usage: delete <num>")
        return commands.cmd_delete(session, args[0])

    elif cmd == "sync":
        if args or kwargs:
            raise ValueError("Usage: sync")
        return commands.cmd_sync(session)

    elif cmd in ("exit", "quit"):
        return "EXIT"

    else:
        raise ValueError(f"Unknown command: {cmd}")


def repl(session: dict[str, Any]) -> None:
    """Run the REPL loop.

    Args:
        session: Current session state
    """
    # Try to enable readline for command history (optional)
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

            # Skip empty lines
            if not line.strip():
                continue

            # Parse and execute
            cmd, args, kwargs = parse_command(line)

            if not cmd:
                continue

            result = execute_command(cmd, args, kwargs, session)

            if result == "EXIT":
                break

            print(result)

        except EOFError:
            # Ctrl-D
            print()
            break

        except KeyboardInterrupt:
            # Ctrl-C
            print()
            continue

        except Exception as e:
            print(f"Error: {e}")


def main() -> None:
    """Main entry point for tk CLI."""
    parser = argparse.ArgumentParser(
        description="tk - A quick CLI app to manage tasks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  tk --profile ~/work/my-profile.json
  tk -p ~/work/my-profile.json

Inside the REPL, use 'new' command to create a profile if it doesn't exist.
        """
    )

    parser.add_argument(
        "--profile", "-p",
        help="Path to profile JSON file"
    )

    args = parser.parse_args()

    # Initialize session
    session = {
        "profile_path": None,
        "profile": None,
        "tasks": None,
        "last_list": []
    }

    # If profile is provided, load it
    if args.profile:
        try:
            prof = profile.load_profile(args.profile)
            session["profile_path"] = args.profile
            session["profile"] = prof

            # Load tasks
            tasks_data = data.load_tasks(prof["data_path"])
            session["tasks"] = tasks_data

        except FileNotFoundError:
            print(f"Profile not found: {args.profile}")
            print("Use 'new' command to create it, or check the path.")
            print()

        except Exception as e:
            print(f"Error loading profile: {e}")
            sys.exit(1)

    # Start REPL
    repl(session)


if __name__ == "__main__":
    main()
