"""Lightweight configuration value objects used across session and command layers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True, slots=True)
class AIEndpoint:
    """Provider + model pair that always travel together."""

    provider: str
    model: str

    def display(self) -> str:
        """Format for user-facing output, e.g. ``'claude | claude-haiku-4-5'``."""
        return f"{self.provider} | {self.model}"


@dataclass(frozen=True, slots=True)
class SystemPromptConfig:
    """Resolved system prompt content and its source path."""

    content: Optional[str] = None
    path: Optional[str] = None

    @property
    def is_set(self) -> bool:
        """Return True when a system prompt is configured."""
        return self.content is not None or self.path is not None
