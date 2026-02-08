"""REPL loop and input handling for PolyChat."""

import logging
import time
from pathlib import Path
from typing import Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings

from . import chat
from .ai_runtime import send_message_to_ai, validate_and_get_provider
from .app_state import has_pending_error
from .session_manager import SessionManager
from .commands import CommandHandler
from .logging_utils import log_event, sanitize_error_message, summarize_command_args
from .streaming import display_streaming_response


async def repl_loop(
    profile_data: dict,
    chat_data: Optional[dict] = None,
    chat_path: Optional[str] = None,
    system_prompt: Optional[str] = None,
    system_prompt_path: Optional[str] = None,
    profile_path: Optional[str] = None,
    log_file: Optional[str] = None,
) -> None:
    """Run the REPL loop."""
    helper_ai_name = profile_data.get("default_helper_ai", profile_data["default_ai"])
    helper_model_name = profile_data["models"][helper_ai_name]
    input_mode = profile_data.get("input_mode", "quick")
    if input_mode not in ("quick", "compose"):
        input_mode = "quick"

    # Create SessionManager (replaces SessionState + session_dict)
    manager = SessionManager(
        profile=profile_data,
        current_ai=profile_data["default_ai"],
        current_model=profile_data["models"][profile_data["default_ai"]],
        helper_ai=helper_ai_name,
        helper_model=helper_model_name,
        chat=chat_data,
        system_prompt=system_prompt,
        system_prompt_path=system_prompt_path,
        input_mode=input_mode,
    )

    if chat_data and system_prompt_path and not chat_data["metadata"].get("system_prompt_path"):
        chat.update_metadata(chat_data, system_prompt_path=system_prompt_path)

    # Create session_dict for backward compatibility with CommandHandler
    # TODO: Update CommandHandler to accept SessionManager directly (Task #6)
    session_dict = manager.to_dict()
    session_dict["profile_path"] = profile_path
    session_dict["chat_path"] = chat_path
    session_dict["log_file"] = log_file
    cmd_handler = CommandHandler(manager, session_dict)
    chat_metadata = manager.chat.get("metadata", {}) if isinstance(manager.chat, dict) else {}
    log_event(
        "session_start",
        level=logging.INFO,
        profile_file=profile_path,
        chat_file=chat_path,
        log_file=log_file,
        chats_dir=manager.profile.get("chats_dir"),
        log_dir=manager.profile.get("log_dir"),
        assistant_provider=manager.current_ai,
        assistant_model=manager.current_model,
        helper_provider=manager.helper_ai,
        helper_model=manager.helper_model,
        input_mode=manager.input_mode,
        timeout=manager.profile.get("timeout", 30),
        system_prompt_path=manager.system_prompt_path,
        chat_title=chat_metadata.get("title"),
        chat_summary=chat_metadata.get("summary"),
        message_count=len(manager.chat.get("messages", [])) if isinstance(manager.chat, dict) else 0,
    )

    kb = KeyBindings()

    @kb.add("enter", eager=True)
    def _(event):
        mode = manager.input_mode
        if mode == "quick":
            buffer_text = event.current_buffer.text
            if buffer_text and buffer_text.strip():
                event.current_buffer.validate_and_handle()
            elif buffer_text and not buffer_text.strip():
                event.current_buffer.reset()
        else:
            event.current_buffer.insert_text("\n")

    @kb.add("escape", "enter", eager=True)
    def _(event):
        mode = manager.input_mode
        if mode == "quick":
            event.current_buffer.insert_text("\n")
        else:
            event.current_buffer.validate_and_handle()

    @kb.add("c-j", eager=True)
    def _(event):
        event.current_buffer.validate_and_handle()

    history_file = Path.home() / ".poly-chat-history"
    prompt_session = PromptSession(
        history=FileHistory(str(history_file)),
        key_bindings=kb,
        multiline=True,
    )

    configured_ais = []
    for provider, model in profile_data["models"].items():
        if provider in profile_data.get("api_keys", {}):
            configured_ais.append(f"{provider} ({model})")

    print("=" * 70)
    print("PolyChat - Multi-AI CLI Chat Tool")
    print("=" * 70)
    print(f"Current Provider: {manager.current_ai}")
    print(f"Current Model:    {manager.current_model}")
    print(f"Configured AIs:   {', '.join(configured_ais)}")
    if chat_path:
        print(f"Chat:             {Path(chat_path).name}")
    else:
        print("Chat:             None (use /new or /open)")
    print()
    if manager.input_mode == "quick":
        print("Input Mode:       quick (Enter sends • Option/Alt+Enter inserts new line)")
    else:
        print("Input Mode:       compose (Enter inserts new line • Option/Alt+Enter sends)")
    print("Ctrl+J also sends in both modes")
    print("Type /help for commands • Ctrl+D to exit")
    print("=" * 70)
    print()

    while True:
        try:
            if has_pending_error(chat_data) and not manager.retry_mode:
                print("[⚠️  PENDING ERROR - Use /retry to retry or /secret to ask separately]")
            elif manager.retry_mode:
                print("[🔄 RETRY MODE - Use /apply to accept, /cancel to abort]")
            elif manager.secret_mode:
                print("[🔒 SECRET MODE - Messages not saved to history]")

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
                        chat_file=chat_path,
                    )

                    if response == "__EXIT__":
                        log_event(
                            "session_stop",
                            level=logging.INFO,
                            reason="exit_command",
                            chat_file=chat_path,
                            message_count=len(chat_data.get("messages", [])) if chat_data else 0,
                        )
                        print("\nGoodbye!")
                        break

                    elif response.startswith("__NEW_CHAT__:"):
                        new_path = response.split(":", 1)[1]
                        previous_chat = chat_path
                        chat_path = new_path
                        chat_data = chat.load_chat(chat_path)

                        if system_prompt_path:
                            chat.update_metadata(chat_data, system_prompt_path=system_prompt_path)

                        # Use SessionManager to handle chat switching
                        manager.switch_chat(chat_path, chat_data)
                        session_dict["chat"] = manager.chat
                        session_dict["chat_path"] = chat_path

                        log_event(
                            "chat_opened",
                            level=logging.INFO,
                            action="new",
                            chat_file=chat_path,
                            previous_chat_file=previous_chat,
                            message_count=len(chat_data.get("messages", [])),
                        )

                        print(f"Created new chat: {Path(chat_path).name}")
                        print()

                    elif response.startswith("__OPEN_CHAT__:"):
                        new_path = response.split(":", 1)[1]
                        previous_chat = chat_path

                        if chat_path and chat_data:
                            await chat.save_chat(chat_path, chat_data)

                        chat_path = new_path
                        chat_data = chat.load_chat(chat_path)

                        # Use SessionManager to handle chat switching
                        manager.switch_chat(chat_path, chat_data)
                        session_dict["chat"] = manager.chat
                        session_dict["chat_path"] = chat_path

                        log_event(
                            "chat_opened",
                            level=logging.INFO,
                            action="open",
                            chat_file=chat_path,
                            previous_chat_file=previous_chat,
                            message_count=len(chat_data.get("messages", [])),
                        )

                        print(f"Opened chat: {Path(chat_path).name}")
                        print()

                    elif response == "__CLOSE_CHAT__":
                        closed_chat = chat_path
                        closed_count = len(chat_data.get("messages", [])) if chat_data else 0
                        if chat_path and chat_data:
                            await chat.save_chat(chat_path, chat_data)

                        chat_path = None
                        chat_data = None

                        # Use SessionManager to handle chat closing
                        manager.close_chat()
                        session_dict["chat"] = {}
                        session_dict["chat_path"] = None

                        log_event(
                            "chat_closed",
                            level=logging.INFO,
                            reason="close_command",
                            chat_file=closed_chat,
                            message_count=closed_count,
                        )

                        print("Chat closed")
                        print()

                    elif response.startswith("__RENAME_CURRENT__:"):
                        new_path = response.split(":", 1)[1]
                        old_path = chat_path
                        chat_path = new_path
                        session_dict["chat_path"] = chat_path
                        log_event(
                            "chat_renamed",
                            level=logging.INFO,
                            old_chat_file=old_path,
                            new_chat_file=chat_path,
                        )

                        print(f"Chat renamed to: {Path(chat_path).name}")
                        print()

                    elif response.startswith("__DELETE_CURRENT__:"):
                        filename = response.split(":", 1)[1]
                        deleted_chat = chat_path
                        chat_path = None
                        chat_data = None

                        # Use SessionManager to handle chat closing
                        manager.close_chat()
                        session_dict["chat"] = {}
                        session_dict["chat_path"] = None

                        log_event(
                            "chat_deleted",
                            level=logging.INFO,
                            reason="delete_current",
                            chat_file=deleted_chat or filename,
                        )

                        print(f"Deleted and closed chat: {filename}")
                        print()

                    elif response == "__APPLY_RETRY__":
                        retry_user_msg, retry_assistant_msg = manager.get_retry_attempt()
                        if retry_user_msg and retry_assistant_msg:
                            if len(chat_data["messages"]) >= 2:
                                for _ in range(2):
                                    last_index = len(chat_data["messages"]) - 1
                                    chat_data["messages"].pop()
                                    manager.remove_message_hex_id(last_index)

                            chat.add_user_message(chat_data, retry_user_msg)
                            new_msg_index = len(chat_data["messages"]) - 1
                            manager.assign_message_hex_id(new_msg_index)

                            chat.add_assistant_message(
                                chat_data, retry_assistant_msg, manager.current_model
                            )
                            new_msg_index = len(chat_data["messages"]) - 1
                            manager.assign_message_hex_id(new_msg_index)

                            await chat.save_chat(chat_path, chat_data)

                        manager.exit_retry_mode()
                        session_dict["retry_mode"] = False

                        print("Retry applied. Original message replaced.")
                        print()

                    elif response == "__CANCEL_RETRY__":
                        manager.exit_retry_mode()
                        session_dict["retry_mode"] = False

                        print("Retry cancelled. Original message kept.")
                        print()

                    elif response == "__CLEAR_SECRET_CONTEXT__":
                        manager.exit_secret_mode()
                        print("Secret mode disabled. Messages will be saved normally.")
                        print()

                    elif response.startswith("__SECRET_ONESHOT__:"):
                        secret_message = response.split(":", 1)[1]

                        provider_instance, error = validate_and_get_provider(manager)
                        if error:
                            print(f"Error: {error}")
                            print()
                            continue

                        messages = chat.get_messages_for_ai(chat_data)
                        temp_messages = messages + [{"role": "user", "content": secret_message}]

                        try:
                            print(f"\n{manager.current_ai.capitalize()} (secret): ", end="", flush=True)
                            response_stream, metadata = await send_message_to_ai(
                                provider_instance,
                                temp_messages,
                                manager.current_model,
                                manager.system_prompt,
                                provider_name=manager.current_ai,
                                mode="secret_oneshot",
                                chat_path=chat_path,
                            )
                            await display_streaming_response(response_stream, prefix="")
                            print()
                            print()
                        except Exception as e:
                            print(f"\nError: {e}")
                            print()

                        continue

                    elif response:
                        print(response)
                        print()

                    # Sync session_dict changes back to manager
                    # TODO: Remove this once commands use SessionManager directly (Task #6)
                    manager.current_ai = session_dict["current_ai"]
                    manager.current_model = session_dict["current_model"]
                    manager.helper_ai = session_dict.get("helper_ai", manager.helper_ai)
                    manager.helper_model = session_dict.get("helper_model", manager.helper_model)
                    manager.input_mode = session_dict.get("input_mode", manager.input_mode)
                    # Note: retry_mode and secret_mode are read-only in commands for now

                except ValueError as e:
                    command_name, command_args = cmd_handler.parse_command(user_input)
                    log_event(
                        "command_error",
                        level=logging.ERROR,
                        command=command_name,
                        args_summary=summarize_command_args(command_name, command_args),
                        error_type=type(e).__name__,
                        error=sanitize_error_message(str(e)),
                        chat_file=chat_path,
                    )
                    print(f"Error: {e}")
                    print()
                continue

            if not chat_path:
                print("\nNo chat is currently open.")
                print("Use /new to create a new chat or /open to open an existing one.")
                print()
                continue

            if has_pending_error(chat_data):
                print("\n⚠️  Cannot continue - last interaction resulted in an error.")
                print("Use /retry to retry the last message, /secret to ask without saving,")
                print("or /rewind to remove the error and continue from an earlier point.")
                print()
                continue

            provider_instance, error = validate_and_get_provider(manager, chat_path=chat_path)
            if error:
                print(f"Error: {error}")
                print()
                continue

            if manager.secret_mode:
                # Enter secret mode if not already (frozen context)
                try:
                    secret_context = manager.get_secret_context()
                except ValueError:
                    # Not in secret mode yet, freeze context
                    manager.enter_secret_mode(chat.get_messages_for_ai(chat_data))
                    secret_context = manager.get_secret_context()

                temp_messages = secret_context + [{"role": "user", "content": user_input}]

                try:
                    print(f"\n{manager.current_ai.capitalize()} (secret): ", end="", flush=True)
                    response_stream, metadata = await send_message_to_ai(
                        provider_instance,
                        temp_messages,
                        manager.current_model,
                        manager.system_prompt,
                        provider_name=manager.current_ai,
                        mode="secret",
                        chat_path=chat_path,
                    )
                    await display_streaming_response(response_stream, prefix="")
                    print()
                    print()
                except Exception as e:
                    print(f"\nError: {e}")
                    print()

                continue

            if manager.retry_mode:
                # Enter retry mode if not already (frozen context)
                try:
                    retry_context = manager.get_retry_context()
                except ValueError:
                    # Not in retry mode yet, freeze context
                    all_messages = chat.get_messages_for_ai(chat_data)
                    if all_messages and all_messages[-1]["role"] == "assistant":
                        manager.enter_retry_mode(all_messages[:-1])
                    else:
                        manager.enter_retry_mode(all_messages)
                    retry_context = manager.get_retry_context()

                temp_messages = retry_context + [{"role": "user", "content": user_input}]

                try:
                    print(f"\n{manager.current_ai.capitalize()} (retry): ", end="", flush=True)
                    response_stream, metadata = await send_message_to_ai(
                        provider_instance,
                        temp_messages,
                        manager.current_model,
                        manager.system_prompt,
                        provider_name=manager.current_ai,
                        mode="retry",
                        chat_path=chat_path,
                    )
                    response_text = await display_streaming_response(response_stream, prefix="")
                    manager.set_retry_attempt(user_input, response_text)
                    print()
                    print()
                except Exception as e:
                    print(f"\nError: {e}")
                    print()

                continue

            chat.add_user_message(chat_data, user_input)
            new_msg_index = len(chat_data["messages"]) - 1
            manager.assign_message_hex_id(new_msg_index)

            messages = chat.get_messages_for_ai(chat_data)

            try:
                print(f"\n{manager.current_ai.capitalize()}: ", end="", flush=True)
                response_stream, metadata = await send_message_to_ai(
                    provider_instance,
                    messages,
                    manager.current_model,
                    manager.system_prompt,
                    provider_name=manager.current_ai,
                    mode="normal",
                    chat_path=chat_path,
                )
                response_text = await display_streaming_response(response_stream, prefix="")

                actual_model = metadata.get("model", manager.current_model)
                chat.add_assistant_message(chat_data, response_text, actual_model)
                new_msg_index = len(chat_data["messages"]) - 1
                manager.assign_message_hex_id(new_msg_index)
                await chat.save_chat(chat_path, chat_data)

                if "usage" in metadata:
                    usage = metadata["usage"]
                    print(f"\n[Tokens: {usage.get('total_tokens', 'N/A')}]")

                print()

            except KeyboardInterrupt:
                print("\n[Message cancelled]")
                if chat_data["messages"] and chat_data["messages"][-1]["role"] == "user":
                    last_index = len(chat_data["messages"]) - 1
                    chat_data["messages"].pop()
                    manager.remove_message_hex_id(last_index)
                print()
                continue

            except Exception as e:
                print(f"\nError: {e}")

                if chat_data["messages"] and chat_data["messages"][-1]["role"] == "user":
                    last_index = len(chat_data["messages"]) - 1
                    chat_data["messages"].pop()
                    manager.remove_message_hex_id(last_index)

                sanitized_error = sanitize_error_message(str(e))
                chat.add_error_message(
                    chat_data,
                    sanitized_error,
                    {"provider": manager.current_ai, "model": manager.current_model},
                )
                new_msg_index = len(chat_data["messages"]) - 1
                manager.assign_message_hex_id(new_msg_index)
                await chat.save_chat(chat_path, chat_data)
                print()

        except (EOFError, KeyboardInterrupt):
            log_event(
                "session_stop",
                level=logging.INFO,
                reason="keyboard_interrupt_or_eof",
                chat_file=chat_path,
                message_count=len(chat_data.get("messages", [])) if chat_data else 0,
            )
            print("\nGoodbye!")
            break
