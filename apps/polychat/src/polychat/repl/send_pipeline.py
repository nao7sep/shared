"""AI send/stream pipeline used by the REPL loop."""

from __future__ import annotations

import logging
import time
from typing import Optional

from ..ai.types import Citation
from ..ai.costing import estimate_cost
from ..ai.citations import normalize_citations, resolve_vertex_citation_urls
from ..ai.runtime import send_message_to_ai, validate_and_get_provider
from ..formatting.costs import format_cost_line, format_cost_usd
from ..formatting.citations import format_citation_list
from ..logging import log_event
from ..orchestrator import ChatOrchestrator
from ..orchestration.types import PrintAction, SendAction
from ..session_manager import SessionManager
from ..streaming import display_streaming_response


async def execute_send_action(
    action: SendAction,
    *,
    manager: SessionManager,
    orchestrator: ChatOrchestrator,
    fallback_chat_path: Optional[str],
    fallback_chat_data: Optional[dict],
) -> None:
    """Execute one orchestrator SendAction and print response output."""
    effective_path = action.chat_path if action.chat_path is not None else fallback_chat_path
    effective_data = action.chat_data if action.chat_data is not None else fallback_chat_data

    use_search = (
        action.search_enabled
        if action.search_enabled is not None
        else manager.search_mode
    )
    provider_instance, validation_error = validate_and_get_provider(
        manager,
        chat_path=effective_path,
        search=use_search,
    )
    if validation_error:
        await orchestrator.rollback_pre_send_failure(
            chat_path=effective_path,
            chat_data=effective_data,
            mode=action.mode,
            assistant_hex_id=action.assistant_hex_id,
        )
        print(f"Error: {validation_error}")
        print()
        return
    if provider_instance is None:
        print("Error: provider is unavailable")
        print()
        return

    if action.mode == "retry" and action.assistant_hex_id:
        prefix = f"{manager.current_ai.capitalize()} ({action.assistant_hex_id}): "
    else:
        prefix = f"{manager.current_ai.capitalize()}: "

    try:
        print(prefix, end="", flush=True)
        effective_request_mode: str = action.mode
        if use_search:
            if action.mode == "secret":
                effective_request_mode = "search+secret"
            elif action.mode == "retry":
                effective_request_mode = "search+retry"
            else:
                effective_request_mode = "search"

        response_stream, metadata = await send_message_to_ai(
            provider_instance,
            action.messages,
            manager.current_model,
            manager.system_prompt,
            provider_name=manager.current_ai,
            profile=manager.profile,
            mode=effective_request_mode,
            chat_path=effective_path,
            search=use_search,
        )
        response_text, first_token_time = await display_streaming_response(
            response_stream,
            prefix="",
        )

        citations: list[Citation] = normalize_citations(metadata.get("citations"))
        if citations:
            citations = await resolve_vertex_citation_urls(citations)

        if citations:
            metadata["citations"] = citations
            for line in format_citation_list(citations):
                print(line)

        end_time = time.perf_counter()
        latency_ms = round((end_time - metadata["started"]) * 1000, 1)

        ttft_ms = None
        if first_token_time is not None:
            ttft_ms = round((first_token_time - metadata["started"]) * 1000, 1)

        usage = metadata.get("usage", {})

        cost_line = format_cost_line(manager.current_model, usage)
        if cost_line:
            print()
            print(cost_line)

        cost_est = estimate_cost(manager.current_model, usage)
        log_event(
            "ai_response",
            level=logging.INFO,
            mode=effective_request_mode,
            provider=manager.current_ai,
            model=manager.current_model,
            chat_file=effective_path,
            latency_ms=latency_ms,
            ttft_ms=ttft_ms,
            output_chars=len(response_text),
            input_tokens=usage.get("prompt_tokens"),
            cached_tokens=usage.get("cached_tokens"),
            cache_write_tokens=usage.get("cache_write_tokens"),
            output_tokens=usage.get("completion_tokens"),
            total_tokens=usage.get("total_tokens"),
            estimated_cost=format_cost_usd(cost_est.total_cost) if cost_est is not None else None,
        )

        result = await orchestrator.handle_ai_response(
            response_text,
            effective_path,
            effective_data,
            action.mode,
            user_input=action.retry_user_input,
            assistant_hex_id=action.assistant_hex_id,
            citations=citations,
        )

        if isinstance(result, PrintAction):
            print(result.message)
        print()

    except KeyboardInterrupt:
        cancel_result = await orchestrator.handle_user_cancel(
            effective_data,
            action.mode,
            chat_path=effective_path,
            assistant_hex_id=action.assistant_hex_id,
        )
        print(cancel_result.message)
        print()
        return

    except Exception as exc:
        error_result = await orchestrator.handle_ai_error(
            exc,
            effective_path,
            effective_data,
            action.mode,
            assistant_hex_id=action.assistant_hex_id,
        )
        print(error_result.message)
        print()
        return
