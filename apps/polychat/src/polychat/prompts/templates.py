"""Centralized AI prompt template builders."""

from __future__ import annotations

from pathlib import Path
from typing import Optional


def _load_prompt_from_path(prompt_path: Optional[str], prompt_type: str = "prompt") -> str:
    """Load prompt content from a file path."""
    if prompt_path is None:
        raise ValueError(
            f"{prompt_type}_prompt not configured in profile. "
            f"Add '{prompt_type}_prompt' path to your profile configuration."
        )

    prompt_file = Path(prompt_path)
    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    return prompt_file.read_text(encoding="utf-8")


def build_title_generation_prompt(context_text: str, prompt_path: Optional[str]) -> str:
    """Build helper prompt for title generation."""
    template = _load_prompt_from_path(prompt_path, prompt_type="title")
    return template.replace("{CONTEXT}", context_text)


def build_summary_generation_prompt(context_text: str, prompt_path: Optional[str]) -> str:
    """Build helper prompt for summary generation."""
    template = _load_prompt_from_path(prompt_path, prompt_type="summary")
    return template.replace("{CONTEXT}", context_text)


def build_safety_check_prompt(content_to_check: str, prompt_path: Optional[str]) -> str:
    """Build helper prompt for safety checks."""
    template = _load_prompt_from_path(prompt_path, prompt_type="safety")
    return template.replace("{CONTEXT}", content_to_check)


__all__ = [
    "build_title_generation_prompt",
    "build_summary_generation_prompt",
    "build_safety_check_prompt",
]
