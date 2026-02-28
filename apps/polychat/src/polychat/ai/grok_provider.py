"""Grok (xAI) provider implementation for PolyChat.

Note: Grok uses OpenAI-compatible API.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, AsyncIterator
from openai import (
    AsyncOpenAI,
    APIConnectionError,
    RateLimitError,
    APITimeoutError,
    InternalServerError,
    BadRequestError,
    AuthenticationError,
)
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential_jitter,
    retry_if_exception_type,
)

from ..logging import before_sleep_log_event, log_event
from ..timeouts import (
    DEFAULT_PROFILE_TIMEOUT_SEC,
    RETRY_BACKOFF_INITIAL_SEC,
    RETRY_BACKOFF_MAX_SEC,
    STANDARD_RETRY_ATTEMPTS,
    build_ai_httpx_timeout,
)
from .provider_logging import (
    api_error_after_retries_message,
    authentication_failed_message,
    bad_request_message,
    log_provider_error,
    unexpected_error_message,
)
from .provider_utils import format_chat_messages
from .tools import grok_web_search_tools
from .types import AIResponseMetadata, Citation


if TYPE_CHECKING:
    from ..domain.chat import ChatMessage

class GrokProvider:
    """Grok (xAI) provider implementation.

    Note: Grok uses xAI's Responses API via the OpenAI-compatible SDK.
    """

    def __init__(self, api_key: str, timeout: float = DEFAULT_PROFILE_TIMEOUT_SEC):
        """Initialize Grok provider.

        Args:
            api_key: xAI API key
            timeout: Request timeout in seconds (0 = no timeout, default: 300.0)
        """
        timeout_config = build_ai_httpx_timeout(timeout)

        self.api_key = api_key
        self.timeout = timeout

        # Disable default retries - we handle retries explicitly
        self.client: Any = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.x.ai/v1",
            timeout=timeout_config,
            max_retries=0,
        )

    def format_messages(self, chat_messages: list[ChatMessage]) -> list[dict[str, str]]:
        """Convert Chat format to Grok format."""
        return format_chat_messages(chat_messages)

    @retry(
        retry=retry_if_exception_type(
            (APIConnectionError, RateLimitError, APITimeoutError, InternalServerError)
        ),
        wait=wait_exponential_jitter(
            initial=RETRY_BACKOFF_INITIAL_SEC,
            max=RETRY_BACKOFF_MAX_SEC,
        ),
        stop=stop_after_attempt(STANDARD_RETRY_ATTEMPTS),
        before_sleep=before_sleep_log_event(
            provider="grok",
            operation="_create_response",
            level=logging.WARNING,
        ),
    )
    async def _create_response(
        self,
        model: str,
        input_items: list[dict[str, str]],
        stream: bool,
        search: bool = False,
        max_output_tokens: int | None = None,
    ):
        """Create response via Responses API with retry logic."""
        kwargs: dict[str, object] = {
            "model": model,
            "input": input_items,
            "stream": stream,
        }
        if search:
            kwargs["tools"] = grok_web_search_tools()
        if max_output_tokens is not None:
            kwargs["max_output_tokens"] = max_output_tokens
        return await self.client.responses.create(**kwargs)

    @staticmethod
    def _extract_citations_from_response(payload: object) -> tuple[list[Citation], object]:
        citations: list[Citation] = []
        raw_citations = getattr(payload, "citations", None) or []
        for c in raw_citations:
            if isinstance(c, dict):
                citations.append({"url": c.get("url"), "title": c.get("title")})
            else:
                citations.append(
                    {
                        "url": getattr(c, "url", None),
                        "title": getattr(c, "title", None),
                    }
                )
        output_items = getattr(payload, "output", None)
        if not citations and isinstance(output_items, list):
            for item in output_items:
                if getattr(item, "type", None) == "message":
                    for content in getattr(item, "content", []):
                        for annotation in getattr(content, "annotations", []):
                            if getattr(annotation, "type", None) == "url_citation":
                                citations.append(
                                    {
                                        "url": getattr(annotation, "url", None),
                                        "title": getattr(annotation, "title", None),
                                    }
                                )
        citations = [c for c in citations if c.get("url")]
        return citations, raw_citations

    async def send_message(
        self,
        messages: list[ChatMessage],
        model: str,
        system_prompt: str | None = None,
        stream: bool = True,
        search: bool = False,
        max_output_tokens: int | None = None,
        metadata: AIResponseMetadata | None = None,
    ) -> AsyncIterator[str]:
        """Send message to Grok and yield response chunks.

        Args:
            messages: Chat messages in PolyChat format
            model: Model name
            system_prompt: Optional system prompt
            stream: Whether to stream the response
            search: Whether to enable web search
            metadata: Optional dict to populate with usage info after streaming

        Yields:
            Response text chunks
        """
        if not stream:
            raise ValueError("GrokProvider.send_message requires stream=True")
        try:
            formatted_messages = self.format_messages(messages)

            if system_prompt:
                formatted_messages.insert(0, {"role": "system", "content": system_prompt})

            response = await self._create_response(
                model=model,
                input_items=formatted_messages,
                stream=stream,
                search=search,
                max_output_tokens=max_output_tokens,
            )

            async for event in response:
                event_type = getattr(event, "type", "")

                if event_type == "response.output_text.delta":
                    if event.delta:
                        yield event.delta
                elif event_type == "response.completed":
                    if event.response and event.response.usage and metadata is not None:
                        usage = event.response.usage
                        metadata["usage"] = {
                            "prompt_tokens": usage.input_tokens,
                            "completion_tokens": usage.output_tokens,
                            "total_tokens": usage.total_tokens,
                        }
                        if hasattr(usage, "input_tokens_details"):
                            in_details = usage.input_tokens_details
                            if in_details and hasattr(in_details, "cached_tokens") and in_details.cached_tokens:
                                metadata["usage"]["cached_tokens"] = in_details.cached_tokens
                        if hasattr(usage, "output_tokens_details"):
                            details = usage.output_tokens_details
                            if hasattr(details, "reasoning_tokens"):
                                metadata["usage"]["reasoning_tokens"] = details.reasoning_tokens

                    if event.response and metadata is not None:
                        citations, _ = self._extract_citations_from_response(event.response)
                        if citations:
                            metadata["citations"] = citations

        except AuthenticationError as e:
            log_provider_error("grok", authentication_failed_message(e))
            raise
        except BadRequestError as e:
            log_provider_error(
                "grok",
                bad_request_message(e, detail="check parameters, unsupported features"),
            )
            raise
        except (
            APIConnectionError,
            RateLimitError,
            APITimeoutError,
            InternalServerError,
        ) as e:
            # These are handled by retry decorator, but if all retries fail:
            log_provider_error("grok", api_error_after_retries_message(e))
            raise
        except Exception as e:
            log_provider_error("grok", unexpected_error_message(e))
            raise

    async def get_full_response(
        self,
        messages: list[ChatMessage],
        model: str,
        system_prompt: str | None = None,
        search: bool = False,
        max_output_tokens: int | None = None,
    ) -> tuple[str, dict]:
        """Get full response from Grok."""
        try:
            formatted_messages = self.format_messages(messages)

            if system_prompt:
                formatted_messages.insert(0, {"role": "system", "content": system_prompt})
            response = await self._create_response(
                model=model,
                input_items=formatted_messages,
                stream=False,
                search=search,
                max_output_tokens=max_output_tokens,
            )
            content = response.output_text or ""

            finish_status = "complete"
            for item in getattr(response, "output", []) or []:
                if hasattr(item, "status"):
                    if item.status == "incomplete":
                        log_event(
                            "provider_log",
                            level=logging.WARNING,
                            provider="grok",
                            message="Response incomplete (may be truncated)",
                        )
                        content += "\n[Response was truncated due to length limit]"
                        finish_status = "incomplete"
                    elif item.status == "failed":
                        log_event(
                            "provider_log",
                            level=logging.WARNING,
                            provider="grok",
                            message="Response generation failed",
                        )
                        content = "[Response generation failed]"
                        finish_status = "failed"

            usage = getattr(response, "usage", None)
            usage_summary = {
                "prompt_tokens": usage.input_tokens if usage else 0,
                "completion_tokens": usage.output_tokens if usage else 0,
                "total_tokens": usage.total_tokens if usage else 0,
            }
            metadata: dict[str, Any] = {
                "model": getattr(response, "model", model),
                "finish_status": finish_status,
                "usage": usage_summary,
            }

            if usage and hasattr(usage, "input_tokens_details"):
                details = usage.input_tokens_details
                if hasattr(details, "cached_tokens"):
                    metadata["usage"]["cached_tokens"] = details.cached_tokens
            if usage and hasattr(usage, "output_tokens_details"):
                details = usage.output_tokens_details
                if hasattr(details, "reasoning_tokens"):
                    metadata["usage"]["reasoning_tokens"] = details.reasoning_tokens

            citations, _ = self._extract_citations_from_response(response)
            if citations:
                metadata["citations"] = citations

            log_event(
                "provider_log",
                level=logging.INFO,
                provider="grok",
                message=(
                    f"Response: {metadata['usage']['total_tokens']} tokens, "
                    f"status={finish_status}"
                ),
            )
            return content, metadata

        except AuthenticationError as e:
            log_provider_error("grok", authentication_failed_message(e))
            raise
        except BadRequestError as e:
            log_provider_error(
                "grok",
                bad_request_message(e, detail="check parameters, unsupported features"),
            )
            raise
        except (
            APIConnectionError,
            RateLimitError,
            APITimeoutError,
            InternalServerError,
        ) as e:
            # These are handled by retry decorator, but if all retries fail:
            log_provider_error("grok", api_error_after_retries_message(e))
            raise
        except Exception as e:
            log_provider_error("grok", unexpected_error_message(e))
            raise
