"""Centralized AI prompt templates."""

from __future__ import annotations
from pathlib import Path
from typing import Optional


DEFAULT_ASSISTANT_SYSTEM_PROMPT = "You are a helpful assistant."


def _load_prompt_from_path(prompt_path: Optional[str], prompt_type: str = "prompt") -> str:
    """Load prompt content from a file path.

    Args:
        prompt_path: Absolute path to prompt file (should already be mapped)
        prompt_type: Type of prompt for error messages (e.g., "title", "summary")

    Returns:
        Prompt content

    Raises:
        FileNotFoundError: If prompt file doesn't exist
        ValueError: If prompt_path is None
    """
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
    """Build helper prompt for title generation.

    Args:
        context_text: Conversation context
        prompt_path: Path to title prompt template (already mapped)

    Returns:
        Complete prompt with context substituted
    """
    template = _load_prompt_from_path(prompt_path, prompt_type="title")
    return template.replace("{CONTEXT}", context_text)


def build_summary_generation_prompt(context_text: str, prompt_path: Optional[str]) -> str:
    """Build helper prompt for summary generation.

    Args:
        context_text: Conversation context
        prompt_path: Path to summary prompt template (already mapped)

    Returns:
        Complete prompt with context substituted
    """
    template = _load_prompt_from_path(prompt_path, prompt_type="summary")
    return template.replace("{CONTEXT}", context_text)


def build_safety_check_prompt(content_to_check: str, prompt_path: Optional[str]) -> str:
    """Build helper prompt for safety checks.

    Args:
        content_to_check: Content to analyze
        prompt_path: Path to safety prompt template (already mapped)

    Returns:
        Complete prompt with content substituted
    """
    template = _load_prompt_from_path(prompt_path, prompt_type="safety")
    return template.replace("{CONTENT}", content_to_check)
