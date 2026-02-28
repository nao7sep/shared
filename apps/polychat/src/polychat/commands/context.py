"""Command execution context for explicit dependency wiring."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Protocol

from ..domain.profile import RuntimeProfile
from ..ui.interaction import UserInteractionPort

if TYPE_CHECKING:
    from ..session_manager import SessionManager


class HelperAIInvoker(Protocol):
    """Callable contract for helper-AI invocation wiring."""

    async def __call__(
        self,
        helper_ai: str,
        helper_model: str,
        profile: RuntimeProfile,
        messages: list[dict],
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
