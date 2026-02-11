"""Gemini (Google) provider implementation for PolyChat."""

import logging
from typing import AsyncIterator
from google import genai
from google.genai import types
from google.genai.errors import (
    ClientError,
    ServerError,
)

from ..message_formatter import lines_to_text
from ..timeouts import (
    DEFAULT_PROFILE_TIMEOUT_SEC,
    GEMINI_RETRY_ATTEMPTS,
    GEMINI_RETRY_EXP_BASE,
    GEMINI_RETRY_INITIAL_DELAY_SEC,
    GEMINI_RETRY_JITTER,
    GEMINI_RETRY_MAX_DELAY_SEC,
)
from .tools import gemini_web_search_tools
from .types import AIResponseMetadata

logger = logging.getLogger(__name__)


class GeminiProvider:
    """Gemini (Google) provider implementation."""

    def __init__(self, api_key: str, timeout: float = DEFAULT_PROFILE_TIMEOUT_SEC):
        """Initialize Gemini provider.

        Args:
            api_key: Google API key
            timeout: Request timeout in seconds (0 = no timeout, default: 30.0)
        """
        # Convert timeout from seconds to milliseconds (Gemini SDK uses ms)
        # 0 means no timeout -> use None
        timeout_ms = int(timeout * 1000) if timeout > 0 else None

        # Configure retry policy for transient errors
        retry_policy = types.HttpRetryOptions(
            attempts=GEMINI_RETRY_ATTEMPTS,
            initial_delay=GEMINI_RETRY_INITIAL_DELAY_SEC,
            exp_base=GEMINI_RETRY_EXP_BASE,
            jitter=GEMINI_RETRY_JITTER,
            max_delay=GEMINI_RETRY_MAX_DELAY_SEC,
            http_status_codes=[429, 503, 504],  # Only retry on these codes
        )

        # Create HTTP options with timeout and retry configuration
        http_options = types.HttpOptions(
            timeout=timeout_ms, retry_options=retry_policy
        )

        self.client = genai.Client(
            api_key=api_key,
            http_options=http_options if timeout_ms else types.HttpOptions(retry_options=retry_policy),
        )
        self.api_key = api_key
        self.timeout = timeout

    def format_messages(self, chat_messages: list[dict]) -> list[types.Content]:
        """Convert Chat format to Gemini format.

        Args:
            chat_messages: Messages in PolyChat format

        Returns:
            Messages in Gemini format
        """
        formatted = []
        for msg in chat_messages:
            content = lines_to_text(msg["content"])
            # Gemini uses "user" and "model" roles
            role = "model" if msg["role"] == "assistant" else "user"
            formatted.append(types.Content(role=role, parts=[types.Part(text=content)]))
        return formatted

    @staticmethod
    def _mark_search_executed(metadata: AIResponseMetadata | None, evidence: str) -> None:
        if metadata is None:
            return
        metadata["search_executed"] = True
        evidence_list = metadata.setdefault("search_evidence", [])
        if isinstance(evidence_list, list) and evidence not in evidence_list:
            evidence_list.append(evidence)

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
        """Send message to Gemini and yield response chunks.

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
        try:
            # Format messages
            formatted_messages = self.format_messages(messages)

            # Handle empty messages case
            if not formatted_messages:
                return

            # Build config with system instruction and tools if provided
            tools = gemini_web_search_tools(types) if search else None
            config_kwargs: dict[str, object] = {
                "system_instruction": system_prompt if system_prompt else None,
                "tools": tools,
            }
            if max_output_tokens is not None:
                config_kwargs["max_output_tokens"] = max_output_tokens
            config = types.GenerateContentConfig(**config_kwargs)

            # Timeout and retry are configured in the Client via http_options
            response = await self.client.aio.models.generate_content_stream(
                model=model,
                contents=formatted_messages,
                config=config,
            )

            # Yield chunks and capture final chunk for usage info
            final_chunk = None
            async for chunk in response:
                final_chunk = chunk  # Keep reference to last chunk

                # Check for finish_reason in chunk candidates
                if chunk.candidates:
                    candidate = chunk.candidates[0]
                    if hasattr(candidate, "finish_reason") and candidate.finish_reason:
                        finish_reason = candidate.finish_reason
                        if finish_reason == "SAFETY":
                            logger.warning("Response blocked by safety filter")
                            yield "\n[Response was blocked by safety filter]"
                            return
                        elif finish_reason == "RECITATION":
                            logger.warning("Response blocked due to recitation/copyright")
                            yield "\n[Response was blocked due to copyright concerns]"
                            return
                        elif finish_reason == "MAX_TOKENS":
                            logger.warning("Response truncated due to max tokens")

                # Yield text content
                if chunk.text:
                    yield chunk.text

            # Populate metadata with usage info from final chunk if available
            if metadata is not None and final_chunk and hasattr(final_chunk, "usage_metadata"):
                usage_meta = final_chunk.usage_metadata
                metadata["usage"] = {
                    "prompt_tokens": getattr(usage_meta, "prompt_token_count", 0),
                    "completion_tokens": getattr(usage_meta, "candidates_token_count", 0),
                    "total_tokens": getattr(usage_meta, "total_token_count", 0),
                }

            # Extract citations from grounding_metadata if search was enabled
            if search and metadata is not None and final_chunk and final_chunk.candidates:
                candidate = final_chunk.candidates[0]
                if hasattr(candidate, "grounding_metadata"):
                    grounding = candidate.grounding_metadata
                    chunks = getattr(grounding, "grounding_chunks", None) or []
                    citations = [
                        {"url": chunk.web.uri, "title": chunk.web.title}
                        for chunk in chunks if hasattr(chunk, "web")
                    ]
                    if citations:
                        metadata["citations"] = citations
                    self._mark_search_executed(metadata, "grounding_metadata")

        except ClientError as e:
            # 400-499 errors - don't retry, these are client-side issues
            status_code = getattr(e, "status_code", "unknown")
            logger.error(f"Client error ({status_code}): {e}")
            if status_code == 400:
                logger.error("Bad request - check message format and parameters")
            elif status_code == 403:
                logger.error("Permission denied - check API key and access")
            elif status_code == 429:
                logger.error("Rate limit exceeded - retries exhausted")
            raise
        except ServerError as e:
            # 500-599 errors - retry handled by SDK, but if all retries fail:
            status_code = getattr(e, "status_code", "unknown")
            logger.error(f"Server error ({status_code}) after retries: {e}")
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
        """Get full response from Gemini.

        Args:
            messages: Chat messages in PolyChat format
            model: Model name
            system_prompt: Optional system prompt
            search: Whether to enable web search

        Returns:
            Tuple of (response_text, metadata)
        """
        try:
            # Format messages
            formatted_messages = self.format_messages(messages)

            # Handle empty messages case
            if not formatted_messages:
                return "", {"model": model, "usage": {}}

            # Build config with system instruction and tools if provided
            tools = gemini_web_search_tools(types) if search else None
            config_kwargs: dict[str, object] = {
                "system_instruction": system_prompt if system_prompt else None,
                "tools": tools,
            }
            if max_output_tokens is not None:
                config_kwargs["max_output_tokens"] = max_output_tokens
            config = types.GenerateContentConfig(**config_kwargs)

            # Timeout and retry are configured in the Client via http_options
            response = await self.client.aio.models.generate_content(
                model=model,
                contents=formatted_messages,
                config=config,
            )

            # Check finish_reason for edge cases
            content = ""
            finish_reason = None

            if response.candidates:
                candidate = response.candidates[0]
                finish_reason = getattr(candidate, "finish_reason", "STOP")

                if finish_reason == "SAFETY":
                    logger.warning("Response blocked by safety filter")
                    content = "[Response was blocked by safety filter]"
                elif finish_reason == "RECITATION":
                    logger.warning("Response blocked due to recitation/copyright")
                    content = "[Response was blocked due to copyright concerns]"
                elif finish_reason == "MAX_TOKENS":
                    logger.warning("Response truncated due to max tokens")
                    content = response.text if response.text else ""
                    content += "\n[Response was truncated due to token limit]"
                else:
                    # Normal completion (STOP)
                    content = response.text if response.text else ""

            # Extract metadata
            metadata = {
                "model": model,
                "finish_reason": finish_reason,
                "usage": {
                    "prompt_tokens": (
                        response.usage_metadata.prompt_token_count
                        if hasattr(response, "usage_metadata")
                        else 0
                    ),
                    "completion_tokens": (
                        response.usage_metadata.candidates_token_count
                        if hasattr(response, "usage_metadata")
                        else 0
                    ),
                    "total_tokens": (
                        response.usage_metadata.total_token_count
                        if hasattr(response, "usage_metadata")
                        else 0
                    ),
                },
            }

            # Extract citations from grounding_metadata if search was enabled
            if search and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, "grounding_metadata"):
                    grounding = candidate.grounding_metadata
                    chunks = getattr(grounding, "grounding_chunks", None) or []
                    citations = [
                        {"url": chunk.web.uri, "title": chunk.web.title}
                        for chunk in chunks if hasattr(chunk, "web")
                    ]
                    if citations:
                        metadata["citations"] = citations
                    self._mark_search_executed(metadata, "grounding_metadata")

            logger.info(
                f"Response: {metadata['usage']['total_tokens']} tokens, "
                f"finish_reason={finish_reason}"
            )

            return content, metadata

        except ClientError as e:
            # 400-499 errors - don't retry, these are client-side issues
            status_code = getattr(e, "status_code", "unknown")
            logger.error(f"Client error ({status_code}): {e}")
            if status_code == 400:
                logger.error("Bad request - check message format and parameters")
            elif status_code == 403:
                logger.error("Permission denied - check API key and access")
            elif status_code == 429:
                logger.error("Rate limit exceeded - retries exhausted")
            raise
        except ServerError as e:
            # 500-599 errors - retry handled by SDK, but if all retries fail:
            status_code = getattr(e, "status_code", "unknown")
            logger.error(f"Server error ({status_code}) after retries: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {type(e).__name__}: {e}")
            raise
