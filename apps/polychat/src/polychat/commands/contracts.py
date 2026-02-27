"""Type-check-time contracts for command mixin dependencies."""

from __future__ import annotations

from typing import Any, Optional, Protocol

from ..session_manager import SessionManager
from .context import CommandContext


class CommandDependencies(Protocol):
    """Structural contract implemented by the composed command handler."""

    context: CommandContext
    manager: SessionManager

    def _require_open_chat(
        self, *, need_messages: bool = False, need_metadata: bool = False
    ) -> Optional[dict[str, Any]]:
        ...

    async def _prompt_text(self, prompt: str) -> str:
        ...

    async def _confirm_yes(self, prompt: str) -> bool:
        ...

    async def _notify(self, message: str) -> None:
        ...

    async def _prompt_chat_selection(
        self,
        chats_dir: str,
        *,
        action: str,
        allow_cancel: bool = True,
    ) -> Optional[str]:
        ...

    async def _update_metadata_and_save(self, **metadata_updates: Any) -> None:
        ...

    def _reconcile_provider_modes(self, provider: Optional[str] = None) -> list[str]:
        ...

    def _resolve_chat_path_arg(self, raw_path: str, chats_dir: str) -> str:
        ...

    @staticmethod
    def _to_local_time(timestamp: str, format_str: str) -> str:
        ...

    @staticmethod
    def _message_content_to_text(content: Any) -> str:
        ...
