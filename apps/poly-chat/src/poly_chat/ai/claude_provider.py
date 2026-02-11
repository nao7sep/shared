"""Claude (Anthropic) provider implementation for PolyChat."""

import logging
from typing import AsyncIterator
from anthropic import AsyncAnthropic
from anthropic import (
    RateLimitError,
    BadRequestError,
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    PermissionDeniedError,
    InternalServerError,
    APIStatusError,
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
from .tools import claude_web_search_tools
from .types import AIResponseMetadata

logger = logging.getLogger(__name__)


class ClaudeProvider:
    """Claude (Anthropic) provider implementation."""

    def __init__(self, api_key: str, timeout: float = DEFAULT_PROFILE_TIMEOUT_SEC):
        """Initialize Claude provider.

        Args:
            api_key: Anthropic API key
            timeout: Request timeout in seconds (0 = no timeout, default: 30.0)
        """
        timeout_config = build_ai_httpx_timeout(timeout)

        # Disable SDK retries - we handle retries explicitly with tenacity
        self.client = AsyncAnthropic(
            api_key=api_key, timeout=timeout_config, max_retries=0
        )
        self.api_key = api_key
        self.timeout = timeout

    def format_messages(self, chat_messages: list[dict]) -> list[dict]:
        """Convert Chat format to Claude format.

        Args:
            chat_messages: Messages in PolyChat format

        Returns:
            Messages in Claude format
        """
        formatted = []
        for msg in chat_messages:
            content = lines_to_text(msg["content"])
            formatted.append({"role": msg["role"], "content": content})
        return formatted

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
    async def _create_message(self, **kwargs):
        """Create message with retry logic.

        Args:
            **kwargs: Arguments to pass to client.messages.create()

        Returns:
            API response
        """
        return await self.client.messages.create(**kwargs)

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
    async def _create_message_stream(self, **kwargs):
        """Create message stream with retry logic.

        Args:
            **kwargs: Arguments to pass to client.messages.stream()

        Returns:
            Stream context manager
        """
        return self.client.messages.stream(**kwargs)

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
        """Send message to Claude and yield response chunks.

        Args:
            messages: Chat messages in PolyChat format
            model: Model name
            system_prompt: Optional system prompt
            stream: Whether to stream the response
            search: Whether to enable web search
            thinking: Whether to enable extended thinking/reasoning
            max_output_tokens: Optional cap for provider output tokens
            thinking_budget_tokens: Optional cap for Claude extended-thinking budget
            metadata: Optional dict to populate with usage info after streaming

        Yields:
            Response text chunks
        """
        try:
            # Format messages
            formatted_messages = self.format_messages(messages)

            # Claude handles system prompt separately
            kwargs = {
                "model": model,
                "messages": formatted_messages,
            }

            if max_output_tokens is not None:
                kwargs["max_tokens"] = max_output_tokens
            else:
                kwargs["max_tokens"] = 8192

            if system_prompt:
                kwargs["system"] = system_prompt

            if search:
                kwargs["tools"] = claude_web_search_tools()

            if thinking:
                thinking_config = {"type": "enabled"}
                if thinking_budget_tokens is not None:
                    thinking_config["budget_tokens"] = thinking_budget_tokens
                kwargs["thinking"] = thinking_config

            # Create streaming request with retry logic
            async with await self._create_message_stream(**kwargs) as response_stream:
                async for text in response_stream.text_stream:
                    yield text

                # After stream completes, check stop reason and extract usage
                final_message = await response_stream.get_final_message()

                # Populate metadata with usage info if provided
                if metadata is not None:
                    metadata["usage"] = {
                        "prompt_tokens": final_message.usage.input_tokens,
                        "completion_tokens": final_message.usage.output_tokens,
                        "total_tokens": final_message.usage.input_tokens
                        + final_message.usage.output_tokens,
                    }

                # Extract citations from final_message if search was enabled
                if search and metadata is not None:
                    citations = []
                    for block in final_message.content:
                        if hasattr(block, "citations"):
                            for citation in (block.citations or []):
                                citations.append({
                                    "url": citation.url,
                                    "title": getattr(citation, "title", None)
                                })
                    if citations:
                        metadata["citations"] = citations
                        self._mark_search_executed(metadata, "citations")

                if final_message.stop_reason == "max_tokens":
                    logger.warning("Response truncated due to max_tokens limit")
                    yield "\n[Response was truncated due to token limit]"
                elif final_message.stop_reason in ("end_turn", "pause_turn"):
                    # Normal completion or search pause
                    pass

        except APIStatusError as e:
            # Check for 529 - System overloaded (critical error)
            if e.status_code == 529:
                logger.error(f"Anthropic system overloaded (529): {e}")
                logger.error(
                    "System is under heavy load. Consider implementing backoff or fallback."
                )
            else:
                logger.error(f"API status error ({e.status_code}): {e}")
            raise
        except RateLimitError as e:
            # 429 - Rate limit exceeded, SDK will retry but if all retries fail:
            logger.error(f"Rate limit exceeded after retries: {e}")
            raise
        except BadRequestError as e:
            # 400 - Invalid request, don't retry
            logger.error(f"Bad request: {e}")
            raise
        except AuthenticationError as e:
            # 401 - Invalid API key
            logger.error(f"Authentication failed: {e}")
            raise
        except PermissionDeniedError as e:
            # 403 - No access to resource
            logger.error(f"Permission denied: {e}")
            raise
        except (APIConnectionError, APITimeoutError, InternalServerError) as e:
            # Network/timeout/server errors - SDK will retry, but if all fail:
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
        """Get full response from Claude.

        Args:
            messages: Chat messages in PolyChat format
            model: Model name
            system_prompt: Optional system prompt
            search: Whether to enable web search
            max_output_tokens: Optional cap for provider output tokens
            thinking_budget_tokens: Optional cap for Claude extended-thinking budget

        Returns:
            Tuple of (response_text, metadata)
        """
        try:
            # Format messages
            formatted_messages = self.format_messages(messages)

            # Claude handles system prompt separately
            kwargs = {
                "model": model,
                "messages": formatted_messages,
            }

            if max_output_tokens is not None:
                kwargs["max_tokens"] = max_output_tokens
            else:
                kwargs["max_tokens"] = 8192

            if search:
                kwargs["tools"] = claude_web_search_tools()
            if thinking:
                thinking_config = {"type": "enabled"}
                if thinking_budget_tokens is not None:
                    thinking_config["budget_tokens"] = thinking_budget_tokens
                kwargs["thinking"] = thinking_config

            if system_prompt:
                kwargs["system"] = system_prompt

            # Create non-streaming request with retry logic
            response = await self._create_message(**kwargs)

            # Extract response
            content = ""
            for block in response.content:
                if hasattr(block, "text"):
                    content += block.text

            # Check stop reason for edge cases
            stop_reason = response.stop_reason
            if stop_reason == "max_tokens":
                logger.warning("Response truncated due to max_tokens limit")
                content += "\n[Response was truncated due to token limit]"

            # Extract metadata
            metadata = {
                "model": response.model,
                "stop_reason": stop_reason,
                "usage": {
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens
                    + response.usage.output_tokens,
                },
            }

            # Extract citations if search was enabled
            if search:
                citations = []
                for block in response.content:
                    if hasattr(block, "citations"):
                        for citation in (block.citations or []):
                            citations.append({
                                "url": citation.url,
                                "title": getattr(citation, "title", None)
                            })
                if citations:
                    metadata["citations"] = citations
                    self._mark_search_executed(metadata, "citations")

            logger.info(
                f"Response: {metadata['usage']['total_tokens']} tokens, "
                f"stop_reason={stop_reason}"
            )

            return content, metadata

        except APIStatusError as e:
            # Check for 529 - System overloaded (critical error)
            if e.status_code == 529:
                logger.error(f"Anthropic system overloaded (529): {e}")
                logger.error(
                    "System is under heavy load. Consider implementing backoff or fallback."
                )
            else:
                logger.error(f"API status error ({e.status_code}): {e}")
            raise
        except RateLimitError as e:
            # 429 - Rate limit exceeded, SDK will retry but if all retries fail:
            logger.error(f"Rate limit exceeded after retries: {e}")
            raise
        except BadRequestError as e:
            # 400 - Invalid request, don't retry
            logger.error(f"Bad request: {e}")
            raise
        except AuthenticationError as e:
            # 401 - Invalid API key
            logger.error(f"Authentication failed: {e}")
            raise
        except PermissionDeniedError as e:
            # 403 - No access to resource
            logger.error(f"Permission denied: {e}")
            raise
        except (APIConnectionError, APITimeoutError, InternalServerError) as e:
            # Network/timeout/server errors - SDK will retry, but if all fail:
            logger.error(f"API error after retries: {type(e).__name__}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {type(e).__name__}: {e}")
            raise
