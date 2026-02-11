"""Grok (xAI) provider implementation for PolyChat.

Note: Grok uses OpenAI-compatible API.
"""

import logging
from typing import AsyncIterator
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
    before_sleep_log,
)

from ..message_formatter import lines_to_text
from ..timeouts import (
    DEFAULT_PROFILE_TIMEOUT_SEC,
    RETRY_BACKOFF_INITIAL_SEC,
    RETRY_BACKOFF_MAX_SEC,
    STANDARD_RETRY_ATTEMPTS,
    build_ai_httpx_timeout,
)
from .tools import grok_web_search_tools
from .types import AIResponseMetadata

logger = logging.getLogger(__name__)


class GrokProvider:
    """Grok (xAI) provider implementation.

    Note: Grok uses xAI's Responses API via the OpenAI-compatible SDK.
    """

    def __init__(self, api_key: str, timeout: float = DEFAULT_PROFILE_TIMEOUT_SEC):
        """Initialize Grok provider.

        Args:
            api_key: xAI API key
            timeout: Request timeout in seconds (0 = no timeout, default: 30.0)
        """
        timeout_config = build_ai_httpx_timeout(timeout)

        self.api_key = api_key
        self.timeout = timeout

        # Disable default retries - we handle retries explicitly
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.x.ai/v1",
            timeout=timeout_config,
            max_retries=0,
        )

    def format_messages(self, chat_messages: list[dict]) -> list[dict]:
        """Convert Chat format to Grok format."""
        formatted = []
        for msg in chat_messages:
            content = lines_to_text(msg["content"])
            formatted.append({"role": msg["role"], "content": content})
        return formatted

    @staticmethod
    def _emit_thought(metadata: AIResponseMetadata | None, chunk: str | None) -> None:
        if metadata is None or not chunk:
            return
        thoughts = metadata.setdefault("thoughts", [])
        if isinstance(thoughts, list):
            thoughts.append(chunk)
        callback = metadata.get("thought_callback")
        if callable(callback):
            try:
                callback(chunk)
            except Exception:
                pass

    @staticmethod
    def _mark_search_executed(metadata: AIResponseMetadata | None, evidence: str) -> None:
        if metadata is None:
            return
        metadata["search_executed"] = True
        evidence_list = metadata.setdefault("search_evidence", [])
        if isinstance(evidence_list, list) and evidence not in evidence_list:
            evidence_list.append(evidence)

    @retry(
        retry=retry_if_exception_type(
            (APIConnectionError, RateLimitError, APITimeoutError, InternalServerError)
        ),
        wait=wait_exponential_jitter(
            initial=RETRY_BACKOFF_INITIAL_SEC,
            max=RETRY_BACKOFF_MAX_SEC,
        ),
        stop=stop_after_attempt(STANDARD_RETRY_ATTEMPTS),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def _create_response(
        self,
        model: str,
        input_items: list[dict],
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
    def _extract_citations_from_response(payload: object) -> tuple[list[dict], object]:
        citations = []
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
        if not citations and getattr(payload, "output", None):
            for item in payload.output:
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
        messages: list[dict],
        model: str,
        system_prompt: str | None = None,
        stream: bool = True,
        search: bool = False,
        thinking: bool = False,
        max_output_tokens: int | None = None,
        thinking_budget_tokens: int | None = None,
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
                if "web_search" in event_type:
                    self._mark_search_executed(metadata, event_type)

                if event_type == "response.output_text.delta":
                    if event.delta:
                        yield event.delta
                elif "reasoning" in event_type:
                    delta = getattr(event, "delta", None)
                    if isinstance(delta, str) and delta:
                        self._emit_thought(metadata, delta)
                elif event_type == "response.completed":
                    if event.response and event.response.usage and metadata is not None:
                        usage = event.response.usage
                        metadata["usage"] = {
                            "prompt_tokens": usage.input_tokens,
                            "completion_tokens": usage.output_tokens,
                            "total_tokens": usage.total_tokens,
                        }
                        if hasattr(usage, "output_tokens_details"):
                            details = usage.output_tokens_details
                            if hasattr(details, "reasoning_tokens"):
                                metadata["usage"]["reasoning_tokens"] = details.reasoning_tokens

                    if event.response and metadata is not None:
                        citations, _ = self._extract_citations_from_response(event.response)
                        if citations:
                            metadata["citations"] = citations
                            self._mark_search_executed(metadata, "citations")

        except AuthenticationError as e:
            logger.error(f"Authentication failed: {e}")
            raise
        except BadRequestError as e:
            logger.error(f"Bad request (check parameters, unsupported features): {e}")
            raise
        except (
            APIConnectionError,
            RateLimitError,
            APITimeoutError,
            InternalServerError,
        ) as e:
            # These are handled by retry decorator, but if all retries fail:
            logger.error(f"API error after retries: {type(e).__name__}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {type(e).__name__}: {e}")
            raise

    async def get_full_response(
        self,
        messages: list[dict],
        model: str,
        system_prompt: str | None = None,
        search: bool = False,
        thinking: bool = False,
        max_output_tokens: int | None = None,
        thinking_budget_tokens: int | None = None,
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
                        logger.warning("Response incomplete (may be truncated)")
                        content += "\n[Response was truncated due to length limit]"
                        finish_status = "incomplete"
                    elif item.status == "failed":
                        logger.warning("Response generation failed")
                        content = "[Response generation failed]"
                        finish_status = "failed"

            usage = getattr(response, "usage", None)
            metadata = {
                "model": getattr(response, "model", model),
                "finish_status": finish_status,
                "usage": {
                    "prompt_tokens": usage.input_tokens if usage else 0,
                    "completion_tokens": usage.output_tokens if usage else 0,
                    "total_tokens": usage.total_tokens if usage else 0,
                },
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
                self._mark_search_executed(metadata, "citations")

            logger.info(
                f"Response: {metadata['usage']['total_tokens']} tokens, "
                f"status={finish_status}"
            )
            return content, metadata

        except AuthenticationError as e:
            logger.error(f"Authentication failed: {e}")
            raise
        except BadRequestError as e:
            logger.error(f"Bad request (check parameters, unsupported features): {e}")
            raise
        except (
            APIConnectionError,
            RateLimitError,
            APITimeoutError,
            InternalServerError,
        ) as e:
            # These are handled by retry decorator, but if all retries fail:
            logger.error(f"API error after retries: {type(e).__name__}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {type(e).__name__}: {e}")
            raise
