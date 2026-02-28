"""CLI bootstrap for tk."""

import argparse
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from tk import data, markdown, profile
from tk.errors import TkError
from tk.models import Profile, TaskStore
from tk.repl import repl
from tk.session import Session


def display_profile_info(prof: Profile) -> None:
    """Display profile information on startup."""
    print()
    print("Profile Information:")
    print(f"  Timezone: {prof.timezone}")

    tz = ZoneInfo(prof.timezone)
    now = datetime.now(tz)

    dst_in_effect = bool(now.dst())
    print(f"  DST: {'Yes' if dst_in_effect else 'No'}")
    print(f"  Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Subjective day starts at: {prof.subjective_day_start}")


def main() -> None:
    """Main entry point for tk CLI."""
    parser = argparse.ArgumentParser(
        description="tk - A quick CLI app to manage tasks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a new profile
  tk init --profile ~/work/my-profile.json
  tk init -p ~/work/my-profile.json

  # Start with an existing profile
  tk --profile ~/work/my-profile.json
  tk -p ~/work/my-profile.json
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    parser_new = subparsers.add_parser("init", help="Create a new profile")
    parser_new.add_argument(
        "--profile",
        "-p",
        required=True,
        help="Path where to save the profile",
    )

    parser.add_argument("--profile", "-p", help="Path to profile JSON file")

    args = parser.parse_args()

    from tk import __version__
    print(f"tk {__version__}")

    if args.command == "init":
        try:
            prof = profile.create_profile(args.profile)

            print()
            print(f"Profile created: {args.profile}")

            tasks_data = TaskStore()
            data.save_tasks(prof.data_path, tasks_data)

            markdown.generate_todo([], prof.output_path)

            print(f"Data file: {prof.data_path}")
            print(f"Output file: {prof.output_path}")
            print(f"Timezone: {prof.timezone}")
            print(f"Subjective day starts at: {prof.subjective_day_start}")

            print()
            print(f"Start the app with: tk --profile {args.profile}")

        except TkError as e:
            print(f"\nERROR: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"\nERROR: {e}")
            sys.exit(1)

        return

    session = Session()

    if args.profile:
        try:
            prof = profile.load_profile(args.profile)
            session.profile_path = args.profile
            session.profile = prof

            tasks_data = data.load_tasks(prof.data_path)
            session.tasks = tasks_data

            display_profile_info(prof)

        except FileNotFoundError:
            print(f"\nERROR: Profile not found: {args.profile}")
            print(f"Create it with: tk init --profile {args.profile}")
            sys.exit(1)

        except TkError as e:
            print(f"\nERROR: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"\nERROR: {e}")
            sys.exit(1)
    else:
        print()
        print("ERROR: No profile specified")
        print()
        print("Create a new profile:")
        print("  tk init --profile <path>")
        print()
        print("Or start with an existing profile:")
        print("  tk --profile <path>")
        sys.exit(1)

    repl(session)


if __name__ == "__main__":
    main()
