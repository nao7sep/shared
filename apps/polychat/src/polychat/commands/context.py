"""Command execution context for explicit dependency wiring."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..ui.interaction import UserInteractionPort

if TYPE_CHECKING:
    from ..session_manager import SessionManager


@dataclass(slots=True)
class CommandContext:
    """Shared command runtime dependencies."""

    manager: SessionManager
    interaction: UserInteractionPort
