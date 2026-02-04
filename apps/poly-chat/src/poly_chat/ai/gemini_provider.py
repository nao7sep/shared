"""Gemini (Google) provider implementation for PolyChat."""

from typing import AsyncIterator
from google import genai
from google.genai import types

from ..message_formatter import lines_to_text


class GeminiProvider:
    """Gemini (Google) provider implementation."""

    def __init__(self, api_key: str, timeout: float = 30.0):
        """Initialize Gemini provider.

        Args:
            api_key: Google API key
            timeout: Request timeout in seconds (0 = no timeout, default: 30.0)
        """
        # Convert timeout from seconds to milliseconds (Gemini SDK uses ms)
        # 0 means no timeout -> use None
        timeout_ms = int(timeout * 1000) if timeout > 0 else None

        self.client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=timeout_ms) if timeout_ms else None,
        )
        self.api_key = api_key
        self.timeout = timeout

    def format_messages(self, conversation_messages: list[dict]) -> list[types.Content]:
        """Convert conversation format to Gemini format.

        Args:
            conversation_messages: Messages in PolyChat format

        Returns:
            Messages in Gemini format
        """
        formatted = []
        for msg in conversation_messages:
            content = lines_to_text(msg["content"])
            # Gemini uses "user" and "model" roles
            role = "model" if msg["role"] == "assistant" else "user"
            formatted.append(types.Content(role=role, parts=[types.Part(text=content)]))
        return formatted

    async def send_message(
        self,
        messages: list[dict],
        model: str,
        system_prompt: str | None = None,
        stream: bool = True,
    ) -> AsyncIterator[str]:
        """Send message to Gemini and yield response chunks.

        Args:
            messages: Conversation messages in PolyChat format
            model: Model name
            system_prompt: Optional system prompt
            stream: Whether to stream the response

        Yields:
            Response text chunks
        """
        try:
            # Format messages
            formatted_messages = self.format_messages(messages)

            # Handle empty messages case
            if not formatted_messages:
                return

            # Build config with system instruction if provided
            config = types.GenerateContentConfig(
                system_instruction=system_prompt if system_prompt else None,
            )

            # Timeout is already configured in the Client via http_options
            response = await self.client.aio.models.generate_content_stream(
                model=model,
                contents=formatted_messages,
                config=config,
            )

            # Yield chunks
            async for chunk in response:
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            print(f"\n[ERROR] {error_msg}")
            raise

    async def get_full_response(
        self, messages: list[dict], model: str, system_prompt: str | None = None
    ) -> tuple[str, dict]:
        """Get full response from Gemini.

        Args:
            messages: Conversation messages in PolyChat format
            model: Model name
            system_prompt: Optional system prompt

        Returns:
            Tuple of (response_text, metadata)
        """
        try:
            # Format messages
            formatted_messages = self.format_messages(messages)

            # Handle empty messages case
            if not formatted_messages:
                return "", {"model": model, "usage": {}}

            # Build config with system instruction if provided
            config = types.GenerateContentConfig(
                system_instruction=system_prompt if system_prompt else None,
            )

            # Timeout is already configured in the Client via http_options
            response = await self.client.aio.models.generate_content(
                model=model,
                contents=formatted_messages,
                config=config,
            )

            # Extract response
            content = response.text if response.text else ""

            # Extract metadata
            metadata = {
                "model": model,
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

            return content, metadata

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            print(f"\n[ERROR] {error_msg}")
            raise
