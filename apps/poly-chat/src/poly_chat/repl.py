"""REPL loop and input handling for PolyChat.

This module provides the main interactive loop that:
- Manages user input via prompt_toolkit
- Delegates command execution to CommandHandler
- Delegates orchestration logic to ChatOrchestrator
- Handles AI streaming responses via display_streaming_response
- Maintains SessionManager as single source of truth for state

The REPL is intentionally kept thin, with business logic extracted to
ChatOrchestrator for better separation of concerns and testability.
"""

import logging
import time
import asyncio
from pathlib import Path
from typing import Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings

from . import chat
from .ai_runtime import send_message_to_ai, validate_and_get_provider
from .app_state import has_pending_error
from .session_manager import SessionManager
from .orchestrator import ChatOrchestrator, OrchestratorAction
from .citations import (
    normalize_citations,
    enrich_citation_titles,
    citations_need_enrichment,
)
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

    # Create SessionManager as single runtime source of truth.
    manager = SessionManager(
        profile=profile_data,
        current_ai=profile_data["default_ai"],
        current_model=profile_data["models"][profile_data["default_ai"]],
        helper_ai=helper_ai_name,
        helper_model=helper_model_name,
        chat=chat_data,
        chat_path=chat_path,
        profile_path=profile_path,
        log_file=log_file,
        system_prompt=system_prompt,
        system_prompt_path=system_prompt_path,
        input_mode=input_mode,
    )

    if chat_data and system_prompt_path and not chat_data["metadata"].get("system_prompt"):
        chat.update_metadata(chat_data, system_prompt=system_prompt_path)

    cmd_handler = CommandHandler(manager)
    orchestrator = ChatOrchestrator(manager)
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

    async def execute_send_action(action: OrchestratorAction) -> None:
        """Execute a prepared send action from orchestrator."""
        provider_instance, error = validate_and_get_provider(manager, chat_path=chat_path)
        if error:
            print(f"Error: {error}")
            print()
            return

        # Determine display prefix.
        if action.mode == "retry" and action.assistant_hex_id:
            prefix = f"\n{manager.current_ai.capitalize()} ({action.assistant_hex_id}): "
        else:
            prefix = f"\n{manager.current_ai.capitalize()}: "

        try:
            print(prefix, end="", flush=True)
            use_search = action.search_enabled if action.search_enabled is not None else manager.search_mode
            effective_request_mode = action.mode or "normal"
            if use_search:
                if action.mode == "secret":
                    effective_request_mode = "search+secret"
                elif action.mode == "retry":
                    effective_request_mode = "search+retry"
                else:
                    effective_request_mode = "search"
            response_stream, metadata = await send_message_to_ai(
                provider_instance,
                action.messages or [],
                manager.current_model,
                manager.system_prompt,
                provider_name=manager.current_ai,
                mode=effective_request_mode,
                chat_path=chat_path,
                search=use_search,
            )
            thought_chunks: list[str] = []
            thought_header_printed = False

            def on_thought(chunk: str) -> None:
                nonlocal thought_header_printed
                if not chunk:
                    return
                thought_chunks.append(chunk)
                if not thought_header_printed:
                    print("\n[Thoughts] ", end="", flush=True)
                    thought_header_printed = True
                print(chunk, end="", flush=True)

            metadata["thought_callback"] = on_thought
            response_text = await display_streaming_response(response_stream, prefix="")
            if thought_header_printed:
                print()

            # Display citations if present
            from .streaming import display_citations

            citations = metadata.get("citations")
            citations = normalize_citations(citations)
            if citations and citations_need_enrichment(citations):
                grace_timeout = 0.25
                total_timeout = 6.0
                enrich_task = asyncio.create_task(enrich_citation_titles(citations))
                try:
                    enriched, changed = await asyncio.wait_for(
                        asyncio.shield(enrich_task), timeout=grace_timeout
                    )
                    if changed:
                        citations = enriched
                except asyncio.TimeoutError:
                    print("\n[Collecting citation titles...]", flush=True)
                    try:
                        enriched, changed = await asyncio.wait_for(
                            asyncio.shield(enrich_task),
                            timeout=max(0.0, total_timeout - grace_timeout),
                        )
                        if changed:
                            citations = enriched
                    except asyncio.TimeoutError:
                        enrich_task.cancel()
                        print("[Citation title lookup timed out; showing available sources.]")
                    except Exception:
                        print("[Citation title lookup failed; showing available sources.]")
                except Exception:
                    pass
            if citations:
                metadata["citations"] = citations
            if citations:
                display_citations(citations)
            search_results = metadata.get("search_results")
            thoughts_text = "".join(thought_chunks).strip()
            search_executed = metadata.get("search_executed")
            search_evidence = metadata.get("search_evidence")

            # Calculate latency and log successful AI response
            latency_ms = round((time.perf_counter() - metadata["started"]) * 1000, 1)
            usage = metadata.get("usage", {})

            from .logging_utils import chat_file_label

            log_event(
                "ai_response",
                level=logging.INFO,
                mode=effective_request_mode,
                provider=manager.current_ai,
                model=manager.current_model,
                chat_file=chat_file_label(chat_path),
                latency_ms=latency_ms,
                output_chars=len(response_text),
                input_tokens=usage.get("prompt_tokens"),
                output_tokens=usage.get("completion_tokens"),
                total_tokens=usage.get("total_tokens"),
                citations=len(citations) if citations else None,
                search=use_search,
                search_requested=use_search,
                search_executed=search_executed,
                search_evidence=search_evidence,
                citation_urls=[c.get("url") for c in citations if isinstance(c, dict) and c.get("url")] if citations else None,
                search_results=search_results,
                thought_chars=len(thoughts_text) if thoughts_text else None,
                thoughts=thoughts_text if thoughts_text else None,
            )

            # Handle successful response
            result = await orchestrator.handle_ai_response(
                response_text,
                chat_path,
                chat_data,
                action.mode or "normal",
                user_input=action.retry_user_input,
                assistant_hex_id=action.assistant_hex_id,
                citations=citations,
            )

            if result.action == "print" and result.message:
                print(result.message)
            print()

        except KeyboardInterrupt:
            cancel_result = await orchestrator.handle_user_cancel(
                chat_data,
                action.mode or "normal",
                chat_path=chat_path,
                assistant_hex_id=action.assistant_hex_id,
            )
            print(cancel_result.message)
            print()
            return

        except Exception as e:
            error_result = await orchestrator.handle_ai_error(
                e,
                chat_path,
                chat_data,
                action.mode or "normal",
                assistant_hex_id=action.assistant_hex_id,
            )
            print(error_result.message)
            print()
            return

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

                    # Handle command response through orchestrator
                    action = await orchestrator.handle_command_response(
                        response, chat_path, chat_data
                    )

                    # Process orchestrator action
                    if action.action == "break":
                        log_event(
                            "session_stop",
                            level=logging.INFO,
                            reason="exit_command",
                            chat_file=chat_path,
                            message_count=len(chat_data.get("messages", [])) if chat_data else 0,
                        )
                        print("\nGoodbye!")
                        break

                    elif action.action == "continue":
                        # Update local chat state from action
                        if action.chat_path is not None:
                            chat_path = action.chat_path
                            manager.chat_path = chat_path
                        if action.chat_data is not None:
                            chat_data = action.chat_data

                        # Print message if provided
                        if action.message:
                            print(action.message)
                            print()

                    elif action.action == "print":
                        if action.message:
                            print(action.message)
                            print()

                    elif action.action in ("send_normal", "send_retry", "send_secret"):
                        await execute_send_action(action)

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
                except Exception as e:
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
                    logging.error(
                        "Unexpected command error (command=%s): %s",
                        command_name,
                        e,
                        exc_info=True,
                    )
                    print(f"Error: {e}")
                    print()
                continue

            # Handle user message through orchestrator
            action = await orchestrator.handle_user_message(user_input, chat_path, chat_data)

            # Handle orchestrator action
            if action.action == "print":
                print(action.message)
                print()
                continue

            if action.action in ("send_normal", "send_retry", "send_secret"):
                await execute_send_action(action)
                continue

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
