"""AI send/stream pipeline used by the REPL loop."""

from __future__ import annotations

import logging
import time
from typing import Optional

from ..ai.types import AIResponseMetadata, Citation
from ..ai.costing import estimate_cost
from ..ai.citations import normalize_citations, resolve_vertex_citation_urls
from ..ai.runtime import send_message_to_ai, validate_and_get_provider
from ..formatting.costs import format_cost_line, format_cost_usd
from ..formatting.citations import format_citation_list
from ..logging import log_event, sanitize_error_message
from ..orchestrator import ChatOrchestrator
from ..orchestration.types import PrintAction, SendAction
from ..session_manager import SessionManager
from ..streaming import display_streaming_response


def _resolve_effective_mode(base_mode: str, use_search: bool) -> str:
    """Combine base request mode with search flag."""
    if not use_search:
        return base_mode
    if base_mode == "secret":
        return "search+secret"
    if base_mode == "retry":
        return "search+retry"
    return "search"


async def _process_citations(
    metadata: AIResponseMetadata,
) -> list[Citation]:
    """Normalize, resolve, and display citations from response metadata."""
    citations: list[Citation] = normalize_citations(metadata.get("citations"))
    if citations:
        citations = await resolve_vertex_citation_urls(citations)
    if citations:
        metadata["citations"] = citations
        print()
        for line in format_citation_list(citations):
            print(line)
    return citations


def _log_response_metrics(
    *,
    metadata: AIResponseMetadata,
    response_text: str,
    first_token_time: Optional[float],
    effective_request_mode: str,
    manager: SessionManager,
    effective_path: Optional[str],
) -> None:
    """Calculate timing/cost metrics and emit a structured log event."""
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


def _warn_nonfatal_post_stream_failure(
    *,
    stage: str,
    error: Exception,
    manager: SessionManager,
    effective_path: Optional[str],
    mode: str,
    print_user_warning: bool,
) -> None:
    """Record a non-fatal failure after the response text has already streamed."""
    sanitized_error = sanitize_error_message(str(error))
    try:
        log_event(
            "ai_response_postprocess_warning",
            level=logging.WARNING,
            stage=stage,
            provider=manager.current_ai,
            model=manager.current_model,
            chat_file=effective_path,
            mode=mode,
            error_type=type(error).__name__,
            error=sanitized_error,
        )
    except Exception:
        pass

    logging.warning(
        "Non-fatal AI response post-processing failure (%s): %s",
        stage,
        sanitized_error,
    )

    if print_user_warning:
        print()
        print(f"[Warning: {stage.replace('_', ' ')} failed: {sanitized_error}]")


async def execute_send_action(
    action: SendAction,
    *,
    manager: SessionManager,
    orchestrator: ChatOrchestrator,
) -> None:
    """Execute one orchestrator SendAction and print response output."""
    effective_path = manager.chat_path
    effective_data = manager.chat

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
    provider_resolution_error = validation_error
    if provider_instance is None and provider_resolution_error is None:
        provider_resolution_error = "Provider resolution failed unexpectedly"
        logging.error(
            "Provider resolution returned neither instance nor validation error "
            "(provider=%s, mode=%s, chat=%s)",
            manager.current_ai,
            action.mode,
            effective_path,
        )

    if provider_resolution_error:
        await orchestrator.rollback_pre_send_failure(
            chat_path=effective_path,
            chat_data=effective_data,
            mode=action.mode,
            error_message=provider_resolution_error,
            assistant_hex_id=action.assistant_hex_id,
        )
        print()
        print(f"Error: {provider_resolution_error}")
        return

    if action.mode == "retry" and action.assistant_hex_id:
        prefix = f"{manager.current_ai.capitalize()} ({action.assistant_hex_id}): "
    else:
        prefix = f"{manager.current_ai.capitalize()}: "

    try:
        print()
        print(prefix, end="", flush=True)
        effective_request_mode = _resolve_effective_mode(action.mode, use_search)

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

    except KeyboardInterrupt:
        cancel_result = await orchestrator.handle_user_cancel(
            effective_data,
            action.mode,
            chat_path=effective_path,
            assistant_hex_id=action.assistant_hex_id,
        )
        print()
        print(cancel_result.message)
        return

    except Exception as exc:
        error_result = await orchestrator.handle_ai_error(
            exc,
            effective_path,
            effective_data,
            action.mode,
            user_input=action.user_input,
            assistant_hex_id=action.assistant_hex_id,
        )
        print()
        print(error_result.message)
        return

    citations = normalize_citations(metadata.get("citations"))
    try:
        citations = await _process_citations(metadata)
    except Exception as exc:
        _warn_nonfatal_post_stream_failure(
            stage="citation_processing",
            error=exc,
            manager=manager,
            effective_path=effective_path,
            mode=effective_request_mode,
            print_user_warning=True,
        )

    try:
        _log_response_metrics(
            metadata=metadata,
            response_text=response_text,
            first_token_time=first_token_time,
            effective_request_mode=effective_request_mode,
            manager=manager,
            effective_path=effective_path,
        )
    except Exception as exc:
        _warn_nonfatal_post_stream_failure(
            stage="response_metrics_logging",
            error=exc,
            manager=manager,
            effective_path=effective_path,
            mode=effective_request_mode,
            print_user_warning=False,
        )

    result = await orchestrator.handle_ai_response(
        response_text,
        effective_path,
        effective_data,
        action.mode,
        user_input=action.user_input,
        assistant_hex_id=action.assistant_hex_id,
        citations=citations,
    )

    if isinstance(result, PrintAction):
        print()
        print(result.message)
