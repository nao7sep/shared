"""System prompt loading helpers for session startup/runtime."""

from __future__ import annotations

import json
from typing import Any, Optional

from .. import profile


def load_system_prompt(
    profile_data: dict[str, Any],
    profile_path: Optional[str] = None,
    strict: bool = False,
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Resolve and load system prompt content from profile data."""
    system_prompt = None
    system_prompt_path = None
    warning = None

    prompt_config = profile_data.get("system_prompt")
    if isinstance(prompt_config, str):
        system_prompt_path = prompt_config

        if profile_path:
            try:
                with open(profile_path, "r", encoding="utf-8") as f:
                    original_profile = json.load(f)
                raw_path = original_profile.get("system_prompt")
                if isinstance(raw_path, str):
                    system_prompt_path = raw_path
            except Exception:
                # Fall back to mapped path already loaded into profile_data.
                pass

        try:
            mapped_path = profile.map_system_prompt_path(system_prompt_path)
            if mapped_path is None:
                raise ValueError("System prompt path is required")
            with open(mapped_path, "r", encoding="utf-8") as f:
                system_prompt = f.read().strip()
        except Exception as e:
            if strict:
                raise ValueError(f"Could not load system prompt: {e}") from e
            warning = f"Could not load system prompt: {e}"

    return system_prompt, system_prompt_path, warning
