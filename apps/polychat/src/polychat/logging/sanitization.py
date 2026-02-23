"""Sensitive-data sanitization helpers for logs and user-visible errors."""

import re


def sanitize_error_message(error_msg: str) -> str:
    """Sanitize error messages to remove sensitive information."""
    sanitized = re.sub(r"sk-[A-Za-z0-9]{10,}", "[REDACTED_API_KEY]", error_msg)
    sanitized = re.sub(r"sk-ant-[A-Za-z0-9-]{10,}", "[REDACTED_API_KEY]", sanitized)
    sanitized = re.sub(r"xai-[A-Za-z0-9]{10,}", "[REDACTED_API_KEY]", sanitized)
    sanitized = re.sub(r"pplx-[A-Za-z0-9]{10,}", "[REDACTED_API_KEY]", sanitized)
    sanitized = re.sub(
        r"Bearer\s+[A-Za-z0-9_\-\.]{20,}",
        "Bearer [REDACTED_TOKEN]",
        sanitized,
    )
    sanitized = re.sub(
        r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+",
        "[REDACTED_JWT]",
        sanitized,
    )
    return sanitized
