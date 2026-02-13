"""Centralized AI prompt templates."""

from __future__ import annotations


DEFAULT_ASSISTANT_SYSTEM_PROMPT = "You are a helpful assistant."


def build_title_generation_prompt(context_text: str) -> str:
    """Build helper prompt for title generation."""
    return (
        "Create a descriptive title that captures what this conversation is about.\n\n"
        f"{context_text}\n\n"
        "Requirements:\n"
        "- Write in whichever language dominates the conversation\n"
        "- Plain text only - no formatting, punctuation marks for structure, or quotation marks\n"
        "- Do not include labels like 'Title:' or 'Here is'\n"
        "- Return just the title itself, nothing else"
    )


def build_summary_generation_prompt(context_text: str) -> str:
    """Build helper prompt for summary generation."""
    return (
        "Write a summary that explains what this conversation is about - like an introduction to the topic being discussed.\n\n"
        f"{context_text}\n\n"
        "Requirements:\n"
        "- Write in whichever language dominates the conversation\n"
        "- Describe the subject matter and key points, not the conversation flow\n"
        "- One cohesive paragraph\n"
        "- Plain text only - no formatting, headings, or bullets\n"
        "- Do not include labels like 'Summary:' or 'Here is'\n"
        "- Return just the summary itself, nothing else"
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
