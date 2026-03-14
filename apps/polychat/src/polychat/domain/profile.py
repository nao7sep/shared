"""Typed runtime profile model used at profile I/O boundaries."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Mapping

if TYPE_CHECKING:
    from ..ai.types import AILimitsConfig
    from ..keys.loader import KeyConfig


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

_PROFILE_PROMPT_KEYS = (
    "system_prompt",
    "title_prompt",
    "summary_prompt",
    "safety_prompt",
)

_API_KEY_FIELD_ORDER: dict[str, tuple[str, ...]] = {
    "env": ("type", "key"),
    "json": ("type", "path", "key"),
    "keychain": ("type", "service", "account"),
    "credential": ("type", "service", "account"),
    "direct": ("type", "value"),
}

_AI_LIMIT_SECTION_ORDER = ("default", "providers", "helper")
_AI_LIMIT_BLOCK_FIELD_ORDER = ("max_output_tokens", "search_max_output_tokens")


def _ordered_mapping(
    raw: Mapping[str, Any],
    preferred_keys: tuple[str, ...],
) -> dict[str, Any]:
    """Return a dict with known keys first and extras kept afterward."""
    payload: dict[str, Any] = {}
    for key in preferred_keys:
        if key in raw:
            payload[key] = raw[key]
    for key, value in raw.items():
        if key not in payload:
            payload[str(key)] = value
    return payload


def _serialize_api_keys(api_keys: Mapping[str, Any]) -> dict[str, Any]:
    """Serialize API key configs with stable per-type field ordering."""
    payload: dict[str, Any] = {}
    for provider, key_config in api_keys.items():
        if isinstance(key_config, Mapping):
            key_type = str(key_config.get("type", ""))
            preferred_keys = _API_KEY_FIELD_ORDER.get(key_type, ("type",))
            payload[str(provider)] = _ordered_mapping(key_config, preferred_keys)
        else:
            payload[str(provider)] = key_config
    return payload


def _serialize_ai_limit_block(block: Mapping[str, Any]) -> dict[str, Any]:
    """Serialize one ai_limits block with stable known-key ordering."""
    return _ordered_mapping(block, _AI_LIMIT_BLOCK_FIELD_ORDER)


def _serialize_ai_limits(ai_limits: Mapping[str, Any]) -> dict[str, Any]:
    """Serialize ai_limits with stable section and block ordering."""
    payload: dict[str, Any] = {}
    for key in _AI_LIMIT_SECTION_ORDER:
        if key not in ai_limits:
            continue
        value = ai_limits[key]
        if key == "providers" and isinstance(value, Mapping):
            payload[key] = {
                str(provider): _serialize_ai_limit_block(block)
                if isinstance(block, Mapping)
                else block
                for provider, block in value.items()
            }
        elif isinstance(value, Mapping):
            payload[key] = _serialize_ai_limit_block(value)
        else:
            payload[key] = value

    for key, value in ai_limits.items():
        if key not in payload:
            payload[str(key)] = value
    return payload


@dataclass(slots=True)
class RuntimeProfile:
    """Typed runtime profile view consumed by session/CLI layers."""

    default_ai: str
    models: dict[str, str]
    chats_dir: str
    logs_dir: str
    api_keys: dict[str, KeyConfig]
    timeout: int | float
    input_mode: str = "quick"
    default_helper_ai: str | None = None
    system_prompt: str | None = None
    title_prompt: str | None = None
    summary_prompt: str | None = None
    safety_prompt: str | None = None
    ai_limits: AILimitsConfig | None = None
    extras: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, profile: Mapping[str, Any]) -> RuntimeProfile:
        """Create typed runtime profile from raw profile data."""
        if not isinstance(profile, Mapping):
            raise ValueError("Profile must be a mapping")

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

        api_keys: dict[str, KeyConfig] = {}
        for provider, key_config in api_keys_raw.items():
            if not isinstance(key_config, Mapping):
                raise ValueError(
                    f"API key config for '{provider}' must be a dictionary"
                )
            api_keys[str(provider)] = dict(key_config)  # type: ignore[assignment]

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
        ai_limits: AILimitsConfig | None = (
            dict(ai_limits_raw) if isinstance(ai_limits_raw, Mapping) else None  # type: ignore[assignment]
        )

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
        """Serialize runtime profile for JSON persistence."""
        profile: dict[str, Any] = {"default_ai": self.default_ai}
        if self.default_helper_ai is not None:
            profile["default_helper_ai"] = self.default_helper_ai
        profile["models"] = dict(self.models)
        profile["timeout"] = self.timeout
        profile["input_mode"] = self.input_mode
        for key in _PROFILE_PROMPT_KEYS:
            value = getattr(self, key)
            if value is not None:
                profile[key] = value
        profile["chats_dir"] = self.chats_dir
        profile["logs_dir"] = self.logs_dir
        profile["api_keys"] = _serialize_api_keys(self.api_keys)
        if self.ai_limits is not None:
            profile["ai_limits"] = _serialize_ai_limits(self.ai_limits)

        profile.update(self.extras)
        return profile
