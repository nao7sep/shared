"""Async user interaction adapters for command flows."""

from __future__ import annotations

import asyncio
from typing import Optional, Protocol

from prompt_toolkit import prompt as pt_prompt

from .chat_ui import prompt_chat_selection


class UserInteractionPort(Protocol):
    """Minimal async interaction contract used by command handlers."""

    async def prompt_text(self, prompt: str) -> str:
        """Prompt for free-form text input."""

    async def notify(self, message: str) -> None:
        """Display one-way informational output."""

    async def prompt_chat_selection(
        self,
        chats_dir: str,
        *,
        action: str = "open",
        allow_cancel: bool = True,
    ) -> Optional[str]:
        """Prompt for interactive chat selection."""


class ThreadedConsoleInteraction:
    """Console adapter that runs blocking prompts in worker threads."""

    async def prompt_text(self, prompt: str) -> str:
        return await asyncio.to_thread(pt_prompt, prompt)

    async def notify(self, message: str) -> None:
        await asyncio.to_thread(print, message)

    async def prompt_chat_selection(
        self,
        chats_dir: str,
        *,
        action: str = "open",
        allow_cancel: bool = True,
    ) -> Optional[str]:
        return await asyncio.to_thread(
            prompt_chat_selection,
            chats_dir,
            action,
            allow_cancel,
        )
