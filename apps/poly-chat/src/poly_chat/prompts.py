"""Centralized AI prompt templates."""

from __future__ import annotations


DEFAULT_ASSISTANT_SYSTEM_PROMPT = "You are a helpful assistant."


def build_title_generation_prompt(context_text: str) -> str:
    """Build helper prompt for title generation."""
    return (
        "You will create a descriptive title for a conversation.\n\n"
        "REQUIRED OUTPUT FORMAT:\n"
        "- Write in whichever language dominates the conversation\n"
        "- Use neutral voice - do not use 'you' or 'your' or address the reader\n"
        "- Plain text only - no markdown, no visual formatting, no quotation marks\n"
        "- Do not include labels like 'Title:' or 'Here is'\n"
        "- Output ONLY the title text, nothing else\n\n"
        "CONVERSATION:\n"
        "---\n"
        f"{context_text}\n"
        "---\n\n"
        "Generate the title now:"
    )


def build_summary_generation_prompt(context_text: str) -> str:
    """Build helper prompt for summary generation."""
    return (
        "You will summarize the subject matter and key points of a conversation.\n\n"
        "REQUIRED OUTPUT FORMAT:\n"
        "- Write in whichever language dominates the conversation\n"
        "- Focus on the topics and ideas, not the back-and-forth exchange\n"
        "- Write in neutral third-person voice\n"
        "- CRITICAL: Do not use 'you', 'your', or address the reader in any way\n"
        "- Write as one cohesive paragraph of plain text\n"
        "- NO formatting: no headings, bullets, markdown, or lists\n"
        "- NO labels: do not start with 'Summary:', 'Here is', or similar phrases\n"
        "- Output ONLY the summary paragraph, nothing else\n\n"
        "CONVERSATION:\n"
        "---\n"
        f"{context_text}\n"
        "---\n\n"
        "Generate the summary paragraph now:"
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
