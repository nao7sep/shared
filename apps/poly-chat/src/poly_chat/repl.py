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
from .app_state import (
    SessionState,
    assign_new_message_hex_id,
    has_pending_error,
    initialize_message_hex_ids,
    reset_chat_scoped_state,
)
from .commands import CommandHandler
from .logging_utils import log_event, sanitize_error_message, summarize_command_args


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

    session = SessionState(
        current_ai=profile_data["default_ai"],
        current_model=profile_data["models"][profile_data["default_ai"]],
        helper_ai=helper_ai_name,
        helper_model=helper_model_name,
        profile=profile_data,
        chat=chat_data if chat_data else {},
        system_prompt=system_prompt,
        system_prompt_path=system_prompt_path,
        input_mode=input_mode,
    )

    if chat_data and system_prompt_path and not chat_data["metadata"].get("system_prompt_path"):
        chat.update_metadata(chat_data, system_prompt_path=system_prompt_path)

    if chat_data:
        initialize_message_hex_ids(session)

    session_dict = {
        "current_ai": session.current_ai,
        "current_model": session.current_model,
        "helper_ai": session.helper_ai,
        "helper_model": session.helper_model,
        "profile": session.profile,
        "profile_path": profile_path,
        "chat": session.chat,
        "chat_path": chat_path,
        "log_file": log_file,
        "system_prompt": session.system_prompt,
        "system_prompt_path": session.system_prompt_path,
        "input_mode": session.input_mode,
        "retry_mode": session.retry_mode,
        "secret_mode": session.secret_mode,
        "message_hex_ids": session.message_hex_ids,
        "hex_id_set": session.hex_id_set,
    }
    cmd_handler = CommandHandler(session_dict)
    chat_metadata = session.chat.get("metadata", {}) if isinstance(session.chat, dict) else {}
    log_event(
        "session_start",
        level=logging.INFO,
        profile_file=profile_path,
        chat_file=chat_path,
        log_file=log_file,
        chats_dir=session.profile.get("chats_dir"),
        log_dir=session.profile.get("log_dir"),
        assistant_provider=session.current_ai,
        assistant_model=session.current_model,
        helper_provider=session.helper_ai,
        helper_model=session.helper_model,
        input_mode=session.input_mode,
        timeout=session.profile.get("timeout", 30),
        system_prompt_path=session.system_prompt_path,
        chat_title=chat_metadata.get("title"),
        chat_summary=chat_metadata.get("summary"),
        message_count=len(session.chat.get("messages", [])) if isinstance(session.chat, dict) else 0,
    )

    kb = KeyBindings()

    @kb.add("enter", eager=True)
    def _(event):
        mode = session_dict.get("input_mode", "quick")
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
        mode = session_dict.get("input_mode", "quick")
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
    print(f"Current Provider: {session.current_ai}")
    print(f"Current Model:    {session.current_model}")
    print(f"Configured AIs:   {', '.join(configured_ais)}")
    if chat_path:
        print(f"Chat:             {Path(chat_path).name}")
    else:
        print("Chat:             None (use /new or /open)")
    print()
    if session.input_mode == "quick":
        print("Input Mode:       quick (Enter sends • Option/Alt+Enter inserts new line)")
    else:
        print("Input Mode:       compose (Enter inserts new line • Option/Alt+Enter sends)")
    print("Ctrl+J also sends in both modes")
    print("Type /help for commands • Ctrl+D to exit")
    print("=" * 70)
    print()

    while True:
        try:
            if has_pending_error(chat_data) and not session.retry_mode:
                print("[⚠️  PENDING ERROR - Use /retry to retry or /secret to ask separately]")
            elif session.retry_mode:
                print("[🔄 RETRY MODE - Use /apply to accept, /cancel to abort]")
            elif session.secret_mode:
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

                        session.chat = chat_data
                        session_dict["chat"] = chat_data
                        session_dict["chat_path"] = chat_path

                        initialize_message_hex_ids(session)
                        reset_chat_scoped_state(session, session_dict)
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

                        session.chat = chat_data
                        session_dict["chat"] = chat_data
                        session_dict["chat_path"] = chat_path

                        initialize_message_hex_ids(session)
                        reset_chat_scoped_state(session, session_dict)
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

                        session.chat = {}
                        session_dict["chat"] = {}
                        session_dict["chat_path"] = None

                        session.message_hex_ids.clear()
                        session.hex_id_set.clear()
                        reset_chat_scoped_state(session, session_dict)
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

                        session.chat = {}
                        session_dict["chat"] = {}
                        session_dict["chat_path"] = None

                        session.message_hex_ids.clear()
                        session.hex_id_set.clear()
                        reset_chat_scoped_state(session, session_dict)
                        log_event(
                            "chat_deleted",
                            level=logging.INFO,
                            reason="delete_current",
                            chat_file=deleted_chat or filename,
                        )

                        print(f"Deleted and closed chat: {filename}")
                        print()

                    elif response == "__APPLY_RETRY__":
                        if session.retry_current_user_msg and session.retry_current_assistant_msg:
                            if len(chat_data["messages"]) >= 2:
                                for _ in range(2):
                                    last_index = len(chat_data["messages"]) - 1
                                    chat_data["messages"].pop()
                                    if last_index in session.message_hex_ids:
                                        hex_to_remove = session.message_hex_ids.pop(last_index)
                                        session.hex_id_set.discard(hex_to_remove)

                            chat.add_user_message(chat_data, session.retry_current_user_msg)
                            new_msg_index = len(chat_data["messages"]) - 1
                            assign_new_message_hex_id(session, new_msg_index)

                            chat.add_assistant_message(
                                chat_data, session.retry_current_assistant_msg, session.current_model
                            )
                            new_msg_index = len(chat_data["messages"]) - 1
                            assign_new_message_hex_id(session, new_msg_index)

                            await chat.save_chat(chat_path, chat_data)

                        session.retry_mode = False
                        session.retry_base_messages.clear()
                        session.retry_current_user_msg = None
                        session.retry_current_assistant_msg = None
                        session_dict["retry_mode"] = False

                        print("Retry applied. Original message replaced.")
                        print()

                    elif response == "__CANCEL_RETRY__":
                        session.retry_mode = False
                        session.retry_base_messages.clear()
                        session.retry_current_user_msg = None
                        session.retry_current_assistant_msg = None
                        session_dict["retry_mode"] = False

                        print("Retry cancelled. Original message kept.")
                        print()

                    elif response == "__CLEAR_SECRET_CONTEXT__":
                        session.secret_base_messages.clear()
                        print("Secret mode disabled. Messages will be saved normally.")
                        print()

                    elif response.startswith("__SECRET_ONESHOT__:"):
                        secret_message = response.split(":", 1)[1]

                        provider_instance, error = validate_and_get_provider(session)
                        if error:
                            print(f"Error: {error}")
                            print()
                            continue

                        messages = chat.get_messages_for_ai(chat_data)
                        temp_messages = messages + [{"role": "user", "content": secret_message}]

                        try:
                            print(f"\n{session.current_ai.capitalize()} (secret): ", end="", flush=True)
                            await send_message_to_ai(
                                provider_instance,
                                temp_messages,
                                session.current_model,
                                session.system_prompt,
                                provider_name=session.current_ai,
                                mode="secret_oneshot",
                                chat_path=chat_path,
                            )
                            print()
                            print()
                        except Exception as e:
                            print(f"\nError: {e}")
                            print()

                        continue

                    elif response:
                        print(response)
                        print()

                    session.current_ai = session_dict["current_ai"]
                    session.current_model = session_dict["current_model"]
                    session.helper_ai = session_dict.get("helper_ai", session.helper_ai)
                    session.helper_model = session_dict.get("helper_model", session.helper_model)
                    session.input_mode = session_dict.get("input_mode", session.input_mode)
                    session.retry_mode = session_dict.get("retry_mode", False)
                    session.secret_mode = session_dict.get("secret_mode", False)

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

            provider_instance, error = validate_and_get_provider(session, chat_path=chat_path)
            if error:
                print(f"Error: {error}")
                print()
                continue

            if session.secret_mode:
                if not session.secret_base_messages:
                    session.secret_base_messages = chat.get_messages_for_ai(chat_data).copy()

                temp_messages = session.secret_base_messages + [{"role": "user", "content": user_input}]

                try:
                    print(f"\n{session.current_ai.capitalize()} (secret): ", end="", flush=True)
                    await send_message_to_ai(
                        provider_instance,
                        temp_messages,
                        session.current_model,
                        session.system_prompt,
                        provider_name=session.current_ai,
                        mode="secret",
                        chat_path=chat_path,
                    )
                    print()
                    print()
                except Exception as e:
                    print(f"\nError: {e}")
                    print()

                continue

            if session.retry_mode:
                if not session.retry_base_messages:
                    all_messages = chat.get_messages_for_ai(chat_data)
                    if all_messages and all_messages[-1]["role"] == "assistant":
                        session.retry_base_messages = all_messages[:-1].copy()
                    else:
                        session.retry_base_messages = all_messages.copy()

                session.retry_current_user_msg = user_input
                temp_messages = session.retry_base_messages + [{"role": "user", "content": user_input}]

                try:
                    print(f"\n{session.current_ai.capitalize()} (retry): ", end="", flush=True)
                    response_text, metadata = await send_message_to_ai(
                        provider_instance,
                        temp_messages,
                        session.current_model,
                        session.system_prompt,
                        provider_name=session.current_ai,
                        mode="retry",
                        chat_path=chat_path,
                    )
                    session.retry_current_assistant_msg = response_text
                    print()
                    print()
                except Exception as e:
                    print(f"\nError: {e}")
                    print()

                continue

            chat.add_user_message(chat_data, user_input)
            new_msg_index = len(chat_data["messages"]) - 1
            assign_new_message_hex_id(session, new_msg_index)

            messages = chat.get_messages_for_ai(chat_data)

            try:
                print(f"\n{session.current_ai.capitalize()}: ", end="", flush=True)
                response_text, metadata = await send_message_to_ai(
                    provider_instance,
                    messages,
                    session.current_model,
                    session.system_prompt,
                    provider_name=session.current_ai,
                    mode="normal",
                    chat_path=chat_path,
                )

                actual_model = metadata.get("model", session.current_model)
                chat.add_assistant_message(chat_data, response_text, actual_model)
                new_msg_index = len(chat_data["messages"]) - 1
                assign_new_message_hex_id(session, new_msg_index)
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
                    if last_index in session.message_hex_ids:
                        hex_to_remove = session.message_hex_ids.pop(last_index)
                        session.hex_id_set.discard(hex_to_remove)
                print()
                continue

            except Exception as e:
                print(f"\nError: {e}")

                if chat_data["messages"] and chat_data["messages"][-1]["role"] == "user":
                    last_index = len(chat_data["messages"]) - 1
                    chat_data["messages"].pop()
                    if last_index in session.message_hex_ids:
                        hex_to_remove = session.message_hex_ids.pop(last_index)
                        session.hex_id_set.discard(hex_to_remove)

                sanitized_error = sanitize_error_message(str(e))
                chat.add_error_message(
                    chat_data,
                    sanitized_error,
                    {"provider": session.current_ai, "model": session.current_model},
                )
                new_msg_index = len(chat_data["messages"]) - 1
                assign_new_message_hex_id(session, new_msg_index)
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
