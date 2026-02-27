"""Command execution context for explicit dependency wiring."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional, Protocol

from ..ui.interaction import UserInteractionPort

if TYPE_CHECKING:
    from ..session_manager import SessionManager


class HelperAIInvoker(Protocol):
    """Callable contract for helper-AI invocation wiring."""

    async def __call__(
        self,
        helper_ai: str,
        helper_model: str,
        profile: dict[str, Any],
        messages: list[dict[str, Any]],
        system_prompt: Optional[str] = None,
        *,
        task: str = "helper_task",
        session: Optional["SessionManager"] = None,
    ) -> str:
        ...


@dataclass(slots=True)
class CommandContext:
    """Shared command runtime dependencies."""

    manager: SessionManager
    interaction: UserInteractionPort
    invoke_helper_ai: HelperAIInvoker
