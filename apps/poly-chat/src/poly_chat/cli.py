"""CLI bootstrap entry point for PolyChat."""

import argparse
import asyncio
import logging
import sys
import time

from . import chat, profile
from .cli_paths import map_cli_path
from .logging_utils import (
    build_run_log_path,
    log_event,
    sanitize_error_message,
    setup_logging,
)
from .repl import repl_loop
from .session_manager import SessionManager
from .timeouts import resolve_profile_timeout


def main() -> None:
    """Main entry point for PolyChat CLI."""
    parser = argparse.ArgumentParser(
        description="PolyChat - Multi-AI CLI Chat Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-p", "--profile", help="Path to profile file (required for normal mode)"
    )

    parser.add_argument(
        "-c",
        "--chat",
        help="Path to chat history file (optional, will prompt if not provided)",
    )

    parser.add_argument(
        "-l", "--log", help="Path to log file for error logging (optional)"
    )

    parser.add_argument(
        "command", nargs="?", help="Command to run (e.g., 'init' to create profile)"
    )

    parser.add_argument(
        "profile_path", nargs="?", help="Profile path (for init command)"
    )

    args = parser.parse_args()
    app_started = time.perf_counter()

    if args.command == "init":
        if not args.profile_path:
            print("Error: profile path required for init command")
            print("Usage: pc init <profile-path>")
            sys.exit(1)
        try:
            mapped_init_profile_path = map_cli_path(args.profile_path, "profile")
            _, messages = profile.create_profile(mapped_init_profile_path)
            # Display status messages returned by create_profile
            for message in messages:
                print(message)
            sys.exit(0)
        except Exception as e:
            print(f"Error creating profile: {e}")
            sys.exit(1)

    if not args.profile:
        print("Error: -p/--profile is required")
        print("Usage: pc -p <profile-path> [-c <chat-path>] [-l <log-path>]")
        sys.exit(1)

    try:
        mapped_profile_path = map_cli_path(args.profile, "profile")
        mapped_chat_path = map_cli_path(args.chat, "chat")
        mapped_log_path = map_cli_path(args.log, "log")

        profile_data = profile.load_profile(mapped_profile_path)
        effective_log_path = mapped_log_path or build_run_log_path(profile_data["logs_dir"])
        setup_logging(effective_log_path)

        chat_path = None
        chat_data = None

        if mapped_chat_path:
            chat_path = mapped_chat_path
            chat_data = chat.load_chat(chat_path)

        system_prompt, system_prompt_path, system_prompt_warning = SessionManager.load_system_prompt(
            profile_data,
            mapped_profile_path,
        )
        if system_prompt_warning:
            print(f"Warning: {system_prompt_warning}")

        log_event(
            "app_start",
            level=logging.INFO,
            profile_file=mapped_profile_path,
            chat_file=mapped_chat_path,
            log_file=effective_log_path,
            chats_dir=profile_data.get("chats_dir"),
            logs_dir=profile_data.get("logs_dir"),
            assistant_provider=profile_data.get("default_ai"),
            assistant_model=profile_data.get("models", {}).get(profile_data.get("default_ai", ""), "(unknown)"),
            helper_provider=profile_data.get("default_helper_ai", profile_data.get("default_ai")),
            helper_model=profile_data.get("models", {}).get(
                profile_data.get("default_helper_ai", profile_data.get("default_ai", "")),
                "(unknown)",
            ),
            input_mode=profile_data.get("input_mode", "quick"),
            timeout=resolve_profile_timeout(profile_data),
            system_prompt_path=system_prompt_path,
        )

        asyncio.run(
            repl_loop(
                profile_data,
                chat_data,
                chat_path,
                system_prompt,
                system_prompt_path,
                mapped_profile_path,
                effective_log_path,
            )
        )
        log_event(
            "app_stop",
            level=logging.INFO,
            reason="normal",
            uptime_ms=round((time.perf_counter() - app_started) * 1000, 1),
        )

    except KeyboardInterrupt:
        log_event(
            "app_stop",
            level=logging.INFO,
            reason="keyboard_interrupt",
            uptime_ms=round((time.perf_counter() - app_started) * 1000, 1),
        )
        print("\nInterrupted")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        log_event(
            "app_stop",
            level=logging.ERROR,
            reason="fatal_error",
            error_type=type(e).__name__,
            error=sanitize_error_message(str(e)),
            uptime_ms=round((time.perf_counter() - app_started) * 1000, 1),
        )
        logging.error("Fatal error: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
