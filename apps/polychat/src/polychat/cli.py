"""CLI bootstrap entry point for PolyChat."""

import argparse
import asyncio
import logging
import sys
import time
from typing import cast

from . import chat, profile, setup_wizard
from .constants import DISPLAY_UNKNOWN
from .logging import (
    build_run_log_path,
    log_event,
    sanitize_error_message,
    setup_logging,
)
from .path_utils import map_path
from .repl import repl_loop
from .session_manager import SessionManager
from .timeouts import resolve_profile_timeout

__all__ = ["main", "sanitize_error_message"]


def _map_cli_arg(path: str | None, arg_name: str) -> str | None:
    """Map CLI path argument with descriptive error messages.

    Args:
        path: Path string or None
        arg_name: Argument name for error messages (e.g., "profile", "chat", "log")

    Returns:
        Mapped absolute path, or None if input was None

    Raises:
        ValueError: With descriptive message including arg_name
    """
    if path is None:
        return None
    try:
        return cast(str, map_path(path))
    except ValueError as e:
        raise ValueError(f"Invalid {arg_name} path: {e}")


def main() -> None:
    """Main entry point for PolyChat CLI."""
    parser = argparse.ArgumentParser(
        prog="polychat",
        description="PolyChat - Multi-AI CLI Chat Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-p",
        "--profile",
        help="Path to profile file (required for normal mode; used by init to create profile)",
    )

    parser.add_argument(
        "-c",
        "--chat",
        help="Path to chat history file (optional; starts without a chat if omitted)",
    )

    parser.add_argument(
        "-l", "--log", help="Path to log file for error logging (optional)"
    )

    parser.add_argument(
        "command", nargs="?", help="Command to run (currently: 'init', 'setup')"
    )

    args = parser.parse_args()
    app_started = time.perf_counter()

    raw_args = sys.argv[1:]

    if args.command == "init":
        if not raw_args or raw_args[0] != "init":
            print("Error: 'init' must be the first argument")
            print("Usage: polychat init -p <profile-path>")
            sys.exit(1)

        if not args.profile:
            print("Error: -p/--profile is required for init command")
            print("Usage: polychat init -p <profile-path>")
            sys.exit(1)
        try:
            mapped_init_profile_path = _map_cli_arg(args.profile, "profile")
            if mapped_init_profile_path is None:
                raise ValueError("Invalid profile path: path is required")
            _, messages = profile.create_profile(mapped_init_profile_path)
            # Display status messages returned by create_profile
            for message in messages:
                print(message)
            sys.exit(0)
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"Error creating profile: {e}")
            sys.exit(1)

    if args.command == "setup":
        if not raw_args or raw_args[0] != "setup":
            print("Error: 'setup' must be the first argument")
            print("Usage: polychat setup")
            sys.exit(1)

        result = setup_wizard.run_setup_wizard()
        if result is None:
            sys.exit(1)

        # Fall through to normal REPL startup with the setup profile
        args.profile = result
        args.chat = None
        args.log = None
        args.command = None

    if args.command:
        print(f"Error: unknown command '{args.command}'")
        print("Supported commands: init, setup")
        print("Usage:")
        print("  polychat init -p <profile-path>")
        print("  polychat setup")
        print("  polychat -p <profile-path> [-c <chat-path>] [-l <log-path>]")
        sys.exit(1)

    if not args.profile:
        print("Error: -p/--profile is required")
        print("Usage: polychat -p <profile-path> [-c <chat-path>] [-l <log-path>]")
        sys.exit(1)

    try:
        # Map CLI path arguments
        mapped_profile_path = _map_cli_arg(args.profile, "profile")
        mapped_chat_path = _map_cli_arg(args.chat, "chat")
        mapped_log_path = _map_cli_arg(args.log, "log")
        if mapped_profile_path is None:
            raise ValueError("Invalid profile path: path is required")

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
            assistant_model=profile_data.get("models", {}).get(profile_data.get("default_ai", ""), DISPLAY_UNKNOWN),
            helper_provider=profile_data.get("default_helper_ai", profile_data.get("default_ai")),
            helper_model=profile_data.get("models", {}).get(
                profile_data.get("default_helper_ai", profile_data.get("default_ai", "")),
                DISPLAY_UNKNOWN,
            ),
            input_mode=profile_data.get("input_mode", "quick"),
            timeout=resolve_profile_timeout(profile_data),
            system_prompt=system_prompt_path,
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
            error=str(e),
            uptime_ms=round((time.perf_counter() - app_started) * 1000, 1),
        )
        logging.error("Fatal error: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
