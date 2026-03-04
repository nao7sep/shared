"""CLI bootstrap entry point for PolyChat."""

import argparse
import asyncio
import logging
import sys
import time
from typing import NoReturn, cast

from . import chat, config as app_config, profile, setup_wizard
from .domain.profile import RuntimeProfile
from .formatting.constants import DISPLAY_UNKNOWN
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
from .ui.segments import begin_output_segment, reset_output_segments
from .ui import prepare_ui_runtime

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


def _print_error_segment(message: str) -> None:
    """Print one error segment using the shared CLI output format."""
    begin_output_segment()
    print(f"ERROR: {message}")


def _exit_startup_error(message: str) -> NoReturn:
    """Print a startup error and exit before entering the REPL."""
    _print_error_segment(message)
    sys.exit(1)


def _load_startup_profile(profile_path: str) -> RuntimeProfile:
    """Load the startup profile with dedicated fast-fail messaging."""
    try:
        return profile.load_profile(profile_path)
    except FileNotFoundError as e:
        _exit_startup_error(str(e))
    except OSError as e:
        _exit_startup_error(f"Could not read profile file {profile_path}: {e}")
    except ValueError as e:
        _exit_startup_error(f"Profile file is invalid: {profile_path}: {e}")


def main() -> None:
    """Main entry point for PolyChat CLI."""
    reset_output_segments()

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
            _print_error_segment("'init' must be the first argument")
            print("Usage: polychat init -p <profile-path>")
            sys.exit(1)

        if not args.profile:
            _print_error_segment("-p/--profile is required for init command")
            print("Usage: polychat init -p <profile-path>")
            sys.exit(1)
        try:
            mapped_init_profile_path = _map_cli_arg(args.profile, "profile")
            if mapped_init_profile_path is None:
                raise ValueError("Invalid profile path: path is required")
            _, messages = profile.create_profile(mapped_init_profile_path)
            # Display status messages returned by create_profile
            if messages:
                begin_output_segment()
                for message in messages:
                    print(message)
            sys.exit(0)
        except ValueError as e:
            _print_error_segment(str(e))
            sys.exit(1)
        except Exception as e:
            _print_error_segment(f"creating profile: {e}")
            sys.exit(1)

    if args.command == "setup":
        if not raw_args or raw_args[0] != "setup":
            _print_error_segment("'setup' must be the first argument")
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
        _print_error_segment(f"unknown command '{args.command}'")
        print("Supported commands: init, setup")
        print("Usage:")
        print("  polychat init -p <profile-path>")
        print("  polychat setup")
        print("  polychat -p <profile-path> [-c <chat-path>] [-l <log-path>]")
        sys.exit(1)

    if not args.profile:
        _print_error_segment("-p/--profile is required")
        print("Usage: polychat -p <profile-path> [-c <chat-path>] [-l <log-path>]")
        sys.exit(1)

    try:
        try:
            startup_app_config = app_config.load_or_create_startup_config()
        except app_config.AppConfigStartupError as e:
            _exit_startup_error(str(e))

        pre_banner_messages = startup_app_config.messages
        if pre_banner_messages:
            begin_output_segment()
            for message in pre_banner_messages:
                print(message)
        app_config_data = startup_app_config.config

        try:
            ui_runtime = prepare_ui_runtime(app_config_data)
        except ValueError as e:
            _exit_startup_error(
                f"App config file is invalid: {startup_app_config.path}: {e}"
            )

        # Map CLI path arguments
        mapped_profile_path = _map_cli_arg(args.profile, "profile")
        mapped_chat_path = _map_cli_arg(args.chat, "chat")
        mapped_log_path = _map_cli_arg(args.log, "log")
        if mapped_profile_path is None:
            raise ValueError("Invalid profile path: path is required")

        profile_data = _load_startup_profile(mapped_profile_path)
        effective_log_path = mapped_log_path or build_run_log_path(
            profile_data.logs_dir
        )
        setup_logging(effective_log_path)

        chat_path = None
        chat_data = None

        if mapped_chat_path:
            chat_path = mapped_chat_path
            chat_data = chat.load_chat(chat_path)

        (system_prompt_content, system_prompt_path), system_prompt_warning = (
            SessionManager.load_system_prompt(
                profile_data,
                mapped_profile_path,
            )
        )
        if system_prompt_warning:
            _print_error_segment(system_prompt_warning)
            sys.exit(1)

        log_event(
            "app_start",
            level=logging.INFO,
            profile_file=mapped_profile_path,
            chat_file=mapped_chat_path,
            log_file=effective_log_path,
            chats_dir=profile_data.chats_dir,
            logs_dir=profile_data.logs_dir,
            assistant_provider=profile_data.default_ai,
            assistant_model=profile_data.models.get(
                profile_data.default_ai, DISPLAY_UNKNOWN
            ),
            helper_provider=profile_data.default_helper_ai or profile_data.default_ai,
            helper_model=profile_data.models.get(
                profile_data.default_helper_ai or profile_data.default_ai,
                DISPLAY_UNKNOWN,
            ),
            input_mode=profile_data.input_mode or "quick",
            timeout=resolve_profile_timeout(profile_data),
            system_prompt=system_prompt_path,
        )

        asyncio.run(
            repl_loop(
                app_config_data,
                ui_runtime.notification_player,
                profile_data,
                chat_data,
                chat_path,
                system_prompt_content,
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
        begin_output_segment()
        print("Interrupted")
        sys.exit(0)
    except Exception as e:
        _print_error_segment(str(e))
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
