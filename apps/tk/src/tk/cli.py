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

    return cmd, args, kwargs


def execute_command(cmd: str, args: list[Any], kwargs: dict[str, Any], session: dict[str, Any]) -> str:
    """Execute a command.

    Args:
        cmd: Command name (supports shortcuts)
        args: Positional arguments
        kwargs: Keyword arguments
        session: Current session state

    Returns:
        Result message

    Raises:
        ValueError: If command is invalid or arguments are wrong
    """
    # Map shortcuts to full commands
    command_aliases = {
        "a": "add",
        "l": "list",
        "h": "history",
        "d": "done",
        "c": "cancel",
        "e": "edit",
        "n": "note",
        "s": "sync",
    }

    # Expand shortcut if provided
    cmd = command_aliases.get(cmd, cmd)

    # Special argument handling after alias expansion
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

    elif cmd in ("done", "cancel"):
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

    elif cmd == "note":
        # First arg is int, rest is note text
        if args:
            try:
                args[0] = int(args[0])
            except ValueError:
                pass

    elif cmd == "date":
        # First arg should be int
        if args:
            try:
                args[0] = int(args[0])
            except ValueError:
                pass

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

    elif cmd == "cancel":
        if len(args) != 1:
            raise ValueError("Usage: cancel <num> [--note <text>] [--date YYYY-MM-DD]")
        note = kwargs.get("note")
        date_str = kwargs.get("date")
        return commands.cmd_cancel(session, args[0], note, date_str)

    elif cmd == "edit":
        if len(args) != 2:
            raise ValueError("Usage: edit <num> <text>")
        return commands.cmd_edit(session, args[0], args[1])

    elif cmd == "delete":
        if len(args) != 1:
            raise ValueError("Usage: delete <num>")
        return commands.cmd_delete(session, args[0])

    elif cmd == "note":
        if len(args) < 1:
            raise ValueError("Usage: note <num> [<text>]")
        num = args[0]
        note_text = " ".join(args[1:]) if len(args) > 1 else None
        return commands.cmd_note(session, num, note_text)

    elif cmd == "date":
        if len(args) != 2:
            raise ValueError("Usage: date <num> <YYYY-MM-DD>")
        return commands.cmd_date(session, args[0], args[1])

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
            print()  # Empty line after command output

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

    # Sync on exit if enabled
    if session.get("profile", {}).get("sync_on_exit", False) and session.get("tasks"):
        from tk import markdown
        markdown.generate_todo(
            session["tasks"]["tasks"],
            session["profile"]["output_path"]
        )

    # Show statistics
    if session.get("tasks"):
        tasks = session["tasks"]["tasks"]
        pending_count = sum(1 for t in tasks if t["status"] == "pending")
        done_count = sum(1 for t in tasks if t["status"] == "done")
        cancelled_count = sum(1 for t in tasks if t["status"] == "cancelled")

        print(f"\nStatistics: {pending_count} pending, {done_count} done, {cancelled_count} cancelled")

    # Empty line after exit for cleaner prompt
    print()


def display_profile_info(prof: dict) -> None:
    """Display profile information on startup.

    Shows timezone, DST status, current time, and subjective day start.
    """
    from datetime import datetime
    from zoneinfo import ZoneInfo

    print("\nProfile Information:")
    print(f"  Timezone: {prof['timezone']}")

    # Get current time in the timezone
    tz = ZoneInfo(prof['timezone'])
    now = datetime.now(tz)

    # Check if DST is currently in effect
    dst_in_effect = bool(now.dst())
    print(f"  DST: {'Yes' if dst_in_effect else 'No'}")

    # Show current time
    print(f"  Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}")

    # Show subjective day start
    print(f"  Subjective day starts at: {prof['subjective_day_start']}")
    print()


def main() -> None:
    """Main entry point for tk CLI."""
    parser = argparse.ArgumentParser(
        description="tk - A quick CLI app to manage tasks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a new profile
  tk new --profile ~/work/my-profile.json
  tk new -p ~/work/my-profile.json

  # Start with an existing profile
  tk --profile ~/work/my-profile.json
  tk -p ~/work/my-profile.json
        """
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # new subcommand
    parser_new = subparsers.add_parser("new", help="Create a new profile")
    parser_new.add_argument(
        "--profile", "-p",
        required=True,
        help="Path where to save the profile"
    )

    # Optional --profile argument for REPL mode
    parser.add_argument(
        "--profile", "-p",
        help="Path to profile JSON file"
    )

    args = parser.parse_args()

    # Handle 'new' command
    if args.command == "new":
        try:
            prof = profile.create_profile(args.profile)
            print(f"Profile created: {args.profile}")

            # Create empty tasks file
            tasks_data = {"tasks": []}
            data.save_tasks(prof["data_path"], tasks_data)

            # Generate empty TODO.md
            from tk import markdown
            markdown.generate_todo([], prof["output_path"])

            print(f"Data file: {prof['data_path']}")
            print(f"Output file: {prof['output_path']}")
            print(f"Timezone: {prof['timezone']}")
            print(f"Subjective day starts at: {prof['subjective_day_start']}")
            print()
            print(f"Start the app with: tk --profile {args.profile}")

        except Exception as e:
            print(f"Error creating profile: {e}")
            sys.exit(1)

        return

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

            # Display profile info
            display_profile_info(prof)

        except FileNotFoundError:
            print(f"Profile not found: {args.profile}")
            print(f"Create it with: tk new {args.profile}")
            print()

        except Exception as e:
            print(f"Error loading profile: {e}")
            sys.exit(1)

    # Start REPL
    repl(session)


if __name__ == "__main__":
    main()
