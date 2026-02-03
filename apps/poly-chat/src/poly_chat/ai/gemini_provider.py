"""Gemini (Google) provider implementation for PolyChat."""

from typing import AsyncIterator
from google import genai
from google.genai import types

from ..message_formatter import lines_to_text


class GeminiProvider:
    """Gemini (Google) provider implementation."""

    def __init__(self, api_key: str):
        """Initialize Gemini provider.

        Args:
            api_key: Google API key
        """
        self.client = genai.Client(api_key=api_key)
        self.api_key = api_key

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
        # Format messages
        formatted_messages = self.format_messages(messages)

        # Handle empty messages case
        if not formatted_messages:
            return

        # Build config with system instruction if provided
        config = types.GenerateContentConfig(
            system_instruction=system_prompt if system_prompt else None,
        )

        # Send message with streaming
        response = await self.client.aio.models.generate_content_stream(
            model=model,
            contents=formatted_messages,
            config=config,
        )

        # Yield chunks
        async for chunk in response:
            if chunk.text:
                yield chunk.text

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
        # Format messages
        formatted_messages = self.format_messages(messages)

        # Handle empty messages case
        if not formatted_messages:
            return "", {"model": model, "usage": {}}

        # Build config with system instruction if provided
        config = types.GenerateContentConfig(
            system_instruction=system_prompt if system_prompt else None,
        )

        # Send message
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
