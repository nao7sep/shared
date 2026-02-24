"""Typed runtime profile model used at profile I/O boundaries."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


_KNOWN_PROFILE_KEYS = {
    "default_ai",
    "default_helper_ai",
    "models",
    "timeout",
    "input_mode",
    "system_prompt",
    "title_prompt",
    "summary_prompt",
    "safety_prompt",
    "chats_dir",
    "logs_dir",
    "api_keys",
    "ai_limits",
}


@dataclass(slots=True)
class RuntimeProfile:
    """Typed runtime profile view consumed by session/CLI layers."""

    default_ai: str
    models: dict[str, str]
    chats_dir: str
    logs_dir: str
    api_keys: dict[str, dict[str, Any]]
    timeout: int | float
    input_mode: str = "quick"
    default_helper_ai: str | None = None
    system_prompt: str | None = None
    title_prompt: str | None = None
    summary_prompt: str | None = None
    safety_prompt: str | None = None
    ai_limits: dict[str, Any] | None = None
    extras: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, profile: Mapping[str, Any]) -> RuntimeProfile:
        """Create typed runtime profile from raw mapped profile data."""
        if not isinstance(profile, Mapping):
            raise ValueError("Profile must be a dictionary-like mapping")

        missing = [
            key
            for key in ("default_ai", "models", "chats_dir", "logs_dir", "api_keys")
            if key not in profile
        ]
        if missing:
            raise ValueError(f"Profile missing required fields: {', '.join(missing)}")

        models_raw = profile.get("models")
        if not isinstance(models_raw, Mapping):
            raise ValueError("'models' must be a dictionary")
        models = {str(key): str(value) for key, value in models_raw.items()}

        api_keys_raw = profile.get("api_keys")
        if not isinstance(api_keys_raw, Mapping):
            raise ValueError("'api_keys' must be a dictionary")

        api_keys: dict[str, dict[str, Any]] = {}
        for provider, key_config in api_keys_raw.items():
            if not isinstance(key_config, Mapping):
                raise ValueError(
                    f"API key config for '{provider}' must be a dictionary"
                )
            api_keys[str(provider)] = dict(key_config)

        timeout = profile.get("timeout", 300)
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
            raise ValueError("'timeout' must be a number")

        input_mode = profile.get("input_mode", "quick")
        if not isinstance(input_mode, str):
            raise ValueError("'input_mode' must be a string")

        extras = {
            str(key): value
            for key, value in profile.items()
            if key not in _KNOWN_PROFILE_KEYS
        }

        ai_limits_raw = profile.get("ai_limits")
        ai_limits = dict(ai_limits_raw) if isinstance(ai_limits_raw, Mapping) else None

        return cls(
            default_ai=str(profile["default_ai"]),
            default_helper_ai=(
                str(profile["default_helper_ai"])
                if profile.get("default_helper_ai") is not None
                else None
            ),
            models=models,
            timeout=timeout,
            input_mode=input_mode,
            system_prompt=(
                str(profile["system_prompt"])
                if profile.get("system_prompt") is not None
                else None
            ),
            title_prompt=(
                str(profile["title_prompt"])
                if profile.get("title_prompt") is not None
                else None
            ),
            summary_prompt=(
                str(profile["summary_prompt"])
                if profile.get("summary_prompt") is not None
                else None
            ),
            safety_prompt=(
                str(profile["safety_prompt"])
                if profile.get("safety_prompt") is not None
                else None
            ),
            chats_dir=str(profile["chats_dir"]),
            logs_dir=str(profile["logs_dir"]),
            api_keys=api_keys,
            ai_limits=ai_limits,
            extras=extras,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize runtime profile to standard dict shape."""
        profile: dict[str, Any] = {
            "default_ai": self.default_ai,
            "models": dict(self.models),
            "timeout": self.timeout,
            "input_mode": self.input_mode,
            "chats_dir": self.chats_dir,
            "logs_dir": self.logs_dir,
            "api_keys": dict(self.api_keys),
        }
        if self.default_helper_ai is not None:
            profile["default_helper_ai"] = self.default_helper_ai
        if self.system_prompt is not None:
            profile["system_prompt"] = self.system_prompt
        if self.title_prompt is not None:
            profile["title_prompt"] = self.title_prompt
        if self.summary_prompt is not None:
            profile["summary_prompt"] = self.summary_prompt
        if self.safety_prompt is not None:
            profile["safety_prompt"] = self.safety_prompt
        if self.ai_limits is not None:
            profile["ai_limits"] = dict(self.ai_limits)

        profile.update(self.extras)
        return profile
