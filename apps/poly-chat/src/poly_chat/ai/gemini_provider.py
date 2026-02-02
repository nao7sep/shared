"""Gemini (Google) provider implementation for PolyChat."""

from typing import AsyncIterator
import google.generativeai as genai

from ..message_formatter import lines_to_text


class GeminiProvider:
    """Gemini (Google) provider implementation."""

    def __init__(self, api_key: str):
        """Initialize Gemini provider.

        Args:
            api_key: Google API key
        """
        genai.configure(api_key=api_key)
        self.api_key = api_key

    def format_messages(
        self,
        conversation_messages: list[dict]
    ) -> list[dict]:
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
            formatted.append({
                "role": role,
                "parts": [content]
            })
        return formatted

    async def send_message(
        self,
        messages: list[dict],
        model: str,
        system_prompt: str | None = None,
        stream: bool = True
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

        # Create model instance
        model_instance = genai.GenerativeModel(
            model_name=model,
            system_instruction=system_prompt if system_prompt else None
        )

        # Gemini expects chat history without the last message
        if formatted_messages:
            history = formatted_messages[:-1]
            last_message = formatted_messages[-1]["parts"][0]
        else:
            history = []
            last_message = ""

        # Create chat
        chat = model_instance.start_chat(history=history)

        # Send message with streaming
        response = await chat.send_message_async(last_message, stream=stream)

        # Yield chunks
        async for chunk in response:
            if chunk.text:
                yield chunk.text

    async def get_full_response(
        self,
        messages: list[dict],
        model: str,
        system_prompt: str | None = None
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

        # Create model instance
        model_instance = genai.GenerativeModel(
            model_name=model,
            system_instruction=system_prompt if system_prompt else None
        )

        # Gemini expects chat history without the last message
        if formatted_messages:
            history = formatted_messages[:-1]
            last_message = formatted_messages[-1]["parts"][0]
        else:
            history = []
            last_message = ""

        # Create chat
        chat = model_instance.start_chat(history=history)

        # Send message
        response = await chat.send_message_async(last_message)

        # Extract response
        content = response.text

        # Extract metadata
        metadata = {
            "model": model,
            "usage": {
                "prompt_tokens": response.usage_metadata.prompt_token_count if hasattr(response, "usage_metadata") else 0,
                "completion_tokens": response.usage_metadata.candidates_token_count if hasattr(response, "usage_metadata") else 0,
                "total_tokens": response.usage_metadata.total_token_count if hasattr(response, "usage_metadata") else 0
            }
        }

        return content, metadata
