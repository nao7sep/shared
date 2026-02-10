"""Centralized AI prompt templates."""

from __future__ import annotations


DEFAULT_ASSISTANT_SYSTEM_PROMPT = "You are a helpful assistant."


def build_title_generation_prompt(context_text: str) -> str:
    """Build helper prompt for title generation."""
    return (
        "Generate a short, descriptive title for this conversation.\n\n"
        f"{context_text}\n\n"
        "Output requirements:\n"
        "- Use the dominant conversation language.\n"
        "- One line only.\n"
        "- Plain text only (no markdown, no bullets, no code fences, no quotes).\n"
        "- Output only the title."
    )


def build_summary_generation_prompt(context_text: str) -> str:
    """Build helper prompt for summary generation."""
    return (
        "Generate a concise summary of this conversation.\n\n"
        f"{context_text}\n\n"
        "Output requirements:\n"
        "- Use the dominant conversation language.\n"
        "- One paragraph only.\n"
        "- Plain text only (no markdown, no bullets, no headings, no code fences).\n"
        "- Output only the summary paragraph."
    )


SAFETY_CHECK_SYSTEM_PROMPT = (
    "You are a safety analyzer. Check the provided content for:\n"
    "1. PII (Personally Identifiable Information) - names, emails, phone numbers, addresses, SSN, etc.\n"
    "2. Credentials - API keys, passwords, tokens, access keys, secrets\n"
    "3. Proprietary Information - confidential business data, trade secrets\n"
    "4. Offensive Content - hate speech, discriminatory language, explicit content\n\n"
    "Respond ONLY in this exact format:\n"
    "PII: [\u2713 None | \u26a0 Found: brief description]\n"
    "CREDENTIALS: [\u2713 None | \u26a0 Found: brief description]\n"
    "PROPRIETARY: [\u2713 None | \u26a0 Found: brief description]\n"
    "OFFENSIVE: [\u2713 None | \u26a0 Found: brief description]\n\n"
    "Keep descriptions brief (one line max). For found items, mention location if checking multiple messages."
)


def build_safety_check_prompt(content_to_check: str) -> str:
    """Build helper prompt for safety checks."""
    return f"Check this content for safety issues:\n\n{content_to_check}"
