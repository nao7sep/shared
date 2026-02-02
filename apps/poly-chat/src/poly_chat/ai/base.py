"""Base interface for AI providers in PolyChat.

This module defines the Protocol that all AI providers must implement.
"""

from typing import Protocol, AsyncIterator


class AIProvider(Protocol):
    """Protocol for AI provider implementations.

    All AI providers must implement these methods to work with PolyChat.
    """

    async def send_message(
        self,
        messages: list[dict],
        model: str,
        system_prompt: str | None = None,
        stream: bool = True
    ) -> AsyncIterator[str]:
        """Send message to AI and yield response chunks if streaming.

        Args:
            messages: List of conversation messages
            model: Model name to use
            system_prompt: Optional system prompt
            stream: Whether to stream the response

        Yields:
            Response text chunks (if streaming)

        Raises:
            Exception: If API call fails
        """
        ...

    async def get_full_response(
        self,
        messages: list[dict],
        model: str,
        system_prompt: str | None = None
    ) -> tuple[str, dict]:
        """Get full response (non-streaming).

        Args:
            messages: List of conversation messages
            model: Model name to use
            system_prompt: Optional system prompt

        Returns:
            Tuple of (response_text, metadata) where metadata contains
            token usage, costs, etc.

        Raises:
            Exception: If API call fails
        """
        ...

    def format_messages(
        self,
        conversation_messages: list[dict]
    ) -> list[dict]:
        """Convert conversation format to provider-specific format.

        Args:
            conversation_messages: Messages in PolyChat format
                [{"role": "user", "content": ["line1", "line2"]}, ...]

        Returns:
            Messages in provider-specific format
        """
        ...
