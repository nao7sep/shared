"""Main PolyChat REPL event loop and local loop helpers."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.history import DummyHistory
from prompt_toolkit.key_binding import KeyBindings

from .. import __version__
from .. import chat
from ..commands import CommandHandler
from ..formatting.constants import BORDERLINE_CHAR, BORDERLINE_WIDTH
from ..logging import log_event, summarize_command_args
from ..orchestrator import ChatOrchestrator
from ..orchestration.types import (
    BreakAction,
    ContinueAction,
    PrintAction,
    SendAction,
)
from ..session.state import has_pending_error, pending_error_guidance
from ..session_manager import SessionManager
from ..domain.chat import ChatDocument
from ..domain.profile import RuntimeProfile
from ..timeouts import resolve_profile_timeout
from ..ui.interaction import ThreadedConsoleInteraction
from .send_pipeline import execute_send_action


EMOJI_MODE_RETRY = "♻️"
EMOJI_MODE_SECRET = "🔒"


def build_key_bindings(manager: SessionManager) -> KeyBindings:
    """Build key bindings for quick/compose input modes."""
    key_bindings = KeyBindings()

    @key_bindings.add("enter", eager=True)
    def _handle_enter(event) -> None:
        mode = manager.input_mode
        if mode == "quick":
            buffer_text = event.current_buffer.text
            if buffer_text and buffer_text.strip():
                event.current_buffer.validate_and_handle()
            elif buffer_text and not buffer_text.strip():
                event.current_buffer.reset()
        else:
            event.current_buffer.insert_text("\n")

    @key_bindings.add("escape", "enter", eager=True)
    def _handle_alt_enter(event) -> None:
        mode = manager.input_mode
        if mode == "quick":
            event.current_buffer.insert_text("\n")
        else:
            event.current_buffer.validate_and_handle()

    @key_bindings.add("c-j", eager=True)
    def _handle_ctrl_j(event) -> None:
        event.current_buffer.validate_and_handle()

    return key_bindings


def create_prompt_session(manager: SessionManager) -> PromptSession:
    """Create prompt-toolkit session for REPL input."""
    return PromptSession(
        # DummyHistory: up-arrow retrieves nothing; no data written to disk.
        # Chat messages are sensitive, so we keep them out of history entirely.
        history=DummyHistory(),
        key_bindings=build_key_bindings(manager),
        multiline=True,
    )


def print_startup_banner(
    manager: SessionManager,
    profile_data: RuntimeProfile,
    chat_path: Optional[str],
) -> None:
    """Print REPL startup context and key usage hints."""
    configured_ais = []
    for provider, model in profile_data.models.items():
        if provider in profile_data.api_keys:
            configured_ais.append(f"{provider} ({model})")

    borderline = BORDERLINE_CHAR * BORDERLINE_WIDTH

    print(borderline)
    print(f"PolyChat {__version__} - Multi-AI CLI Chat Tool")
    print(borderline)
    print(f"Current Provider: {manager.current_ai}")
    print(f"Current Model:    {manager.current_model}")
    print(f"Configured AIs:   {', '.join(configured_ais)}")
    if chat_path:
        print(f"Chat:             {Path(chat_path).name}")
    else:
        print("Chat:             None (use /new or /open)")
    print()
    if manager.input_mode == "quick":
        print("Input Mode:       quick (Enter sends | Option/Alt+Enter inserts new line)")
    else:
        print("Input Mode:       compose (Enter inserts new line | Option/Alt+Enter sends)")
    print("Ctrl+J also sends in both modes")
    print("Type /help for commands • /exit or Ctrl-D to quit")
    print(borderline)


def print_mode_banner(manager: SessionManager, chat_data: Optional[ChatDocument]) -> None:
    """Print mode-state banner shown before each prompt."""
    if has_pending_error(chat_data) and not manager.retry.active:
        print(pending_error_guidance(compact=True))
    elif manager.retry.active:
        print(f"{EMOJI_MODE_RETRY} RETRY MODE - Use /apply to accept, /cancel to abort")
    elif manager.secret.active:
        print(f"{EMOJI_MODE_SECRET} SECRET MODE - Messages not saved to history")


async def repl_loop(
    profile_data: RuntimeProfile,
    chat_data: Optional[ChatDocument] = None,
    chat_path: Optional[str] = None,
    system_prompt: Optional[str] = None,
    system_prompt_path: Optional[str] = None,
    profile_path: Optional[str] = None,
    log_file: Optional[str] = None,
) -> None:
    """Run the REPL loop."""
    default_ai = profile_data.default_ai
    helper_ai = profile_data.default_helper_ai or default_ai

    input_mode = profile_data.input_mode or "quick"
    if input_mode not in ("quick", "compose"):
        input_mode = "quick"

    manager = SessionManager(
        profile=profile_data,
        current_ai=default_ai,
        current_model=profile_data.models[default_ai],
        helper_ai=helper_ai,
        helper_model=profile_data.models[helper_ai],
        chat=chat_data,
        chat_path=chat_path,
        profile_path=profile_path,
        log_file=log_file,
        system_prompt=system_prompt,
        system_prompt_path=system_prompt_path,
        input_mode=input_mode,
    )

    if chat_data and system_prompt_path and not chat_data.metadata.system_prompt:
        chat.update_metadata(chat_data, system_prompt=system_prompt_path)

    cmd_handler = CommandHandler(manager, interaction=ThreadedConsoleInteraction())
    orchestrator = ChatOrchestrator(manager)
    log_event(
        "session_start",
        level=logging.INFO,
        profile_file=profile_path,
        chat_file=chat_path,
        log_file=log_file,
        chats_dir=manager.profile.chats_dir,
        logs_dir=manager.profile.logs_dir,
        assistant_provider=manager.assistant.provider,
        assistant_model=manager.assistant.model,
        helper_provider=manager.helper.provider,
        helper_model=manager.helper.model,
        input_mode=manager.input_mode,
        timeout=resolve_profile_timeout(manager.profile),
        system_prompt=manager.system_prompt_path,
        chat_title=manager.chat.metadata.title,
        chat_summary=manager.chat.metadata.summary,
        message_count=len(manager.chat.messages),
    )

    prompt_session = create_prompt_session(manager)
    print_startup_banner(manager, profile_data, manager.chat_path)

    while True:
        try:
            print()
            print_mode_banner(manager, manager.chat)

            # Empty prompt string is intentional: a visible prefix (e.g.
            # "> ") would be re-printed on every line in compose/multiline
            # mode, breaking the visual layout of longer messages.
            user_input = await prompt_session.prompt_async(
                "",
                multiline=True,
                prompt_continuation=lambda width, line_number, is_soft_wrap: "",
            )

            if not user_input.strip():
                continue

            if cmd_handler.is_command(user_input):
                try:
                    command_name, command_args = cmd_handler.parse_command(user_input)
                    command_started = time.perf_counter()
                    response = await cmd_handler.execute_command(user_input)
                    log_event(
                        "command_exec",
                        level=logging.INFO,
                        command=command_name,
                        args_summary=summarize_command_args(command_name, command_args),
                        elapsed_ms=round((time.perf_counter() - command_started) * 1000, 1),
                        chat_file=manager.chat_path,
                    )

                    action = await orchestrator.handle_command_response(response)

                    if isinstance(action, BreakAction):
                        log_event(
                            "session_stop",
                            level=logging.INFO,
                            reason="exit_command",
                            chat_file=manager.chat_path,
                            message_count=len(manager.chat.messages),
                        )
                        print("Goodbye!")
                        break

                    elif isinstance(action, ContinueAction):
                        if action.message:
                            print(action.message)

                    elif isinstance(action, PrintAction):
                        print(action.message)

                    elif isinstance(action, SendAction):
                        await execute_send_action(
                            action,
                            manager=manager,
                            orchestrator=orchestrator,
                        )

                except ValueError as error:
                    command_name, command_args = cmd_handler.parse_command(user_input)
                    log_event(
                        "command_error",
                        level=logging.ERROR,
                        command=command_name,
                        args_summary=summarize_command_args(command_name, command_args),
                        error_type=type(error).__name__,
                        error=str(error),
                        chat_file=manager.chat_path,
                    )
                    print(f"Error: {error}")
                except Exception as error:
                    command_name, command_args = cmd_handler.parse_command(user_input)
                    log_event(
                        "command_error",
                        level=logging.ERROR,
                        command=command_name,
                        args_summary=summarize_command_args(command_name, command_args),
                        error_type=type(error).__name__,
                        error=str(error),
                        chat_file=manager.chat_path,
                    )
                    logging.error(
                        "Unexpected command error (command=%s): %s",
                        command_name,
                        error,
                        exc_info=True,
                    )
                    print(f"Error: {error}")
                continue

            action = await orchestrator.handle_user_message(user_input)

            if isinstance(action, PrintAction):
                print()
                print(action.message)
                continue

            if isinstance(action, SendAction):
                await execute_send_action(
                    action,
                    manager=manager,
                    orchestrator=orchestrator,
                )
                continue

        except EOFError:
            log_event(
                "session_stop",
                level=logging.INFO,
                reason="eof",
                chat_file=manager.chat_path,
                message_count=len(manager.chat.messages),
            )
            print("Goodbye!")
            break

        except KeyboardInterrupt:
            # Ctrl+C at the prompt clears the current line and returns a
            # fresh prompt.  It must never terminate the application.
            continue

        except Exception as error:
            log_event(
                "repl_error",
                level=logging.ERROR,
                error_type=type(error).__name__,
                error=str(error),
                chat_file=manager.chat_path,
            )
            logging.error("Unexpected REPL error: %s", error, exc_info=True)
            print(f"Error: {error}")
