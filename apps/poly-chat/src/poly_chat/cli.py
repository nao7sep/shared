"""CLI entry point and REPL loop for PolyChat."""

import sys
import json
import asyncio
import argparse
import logging
import re
import time
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings

from . import profile, chat, hex_id
from .commands import CommandHandler
from .keys.loader import load_api_key, validate_api_key
from .streaming import display_streaming_response


# AI provider imports
from .ai.openai_provider import OpenAIProvider
from .ai.claude_provider import ClaudeProvider
from .ai.gemini_provider import GeminiProvider
from .ai.grok_provider import GrokProvider
from .ai.perplexity_provider import PerplexityProvider
from .ai.mistral_provider import MistralProvider
from .ai.deepseek_provider import DeepSeekProvider

# Type alias for provider instances
ProviderInstance = (
    OpenAIProvider
    | ClaudeProvider
    | GeminiProvider
    | GrokProvider
    | PerplexityProvider
    | MistralProvider
    | DeepSeekProvider
)

# Provider class registry
PROVIDER_CLASSES: dict[str, type] = {
    "openai": OpenAIProvider,
    "claude": ClaudeProvider,
    "gemini": GeminiProvider,
    "grok": GrokProvider,
    "perplexity": PerplexityProvider,
    "mistral": MistralProvider,
    "deepseek": DeepSeekProvider,
}


class StructuredTextFormatter(logging.Formatter):
    """Format all log records as human-readable structured blocks."""

    EVENT_KEY_ORDER: dict[str, list[str]] = {
        "app_start": [
            "ts", "level", "profile_file", "chat_file", "log_file",
            "chats_dir", "log_dir",
            "assistant_provider", "assistant_model",
            "helper_provider", "helper_model",
            "input_mode", "timeout", "system_prompt_path",
        ],
        "app_stop": ["ts", "level", "reason", "error_type", "error", "uptime_ms"],
        "session_start": [
            "ts", "level", "profile_file", "chat_file", "log_file",
            "chats_dir", "log_dir",
            "assistant_provider", "assistant_model",
            "helper_provider", "helper_model",
            "input_mode", "timeout", "system_prompt_path",
            "chat_title", "chat_summary", "message_count",
        ],
        "session_stop": ["ts", "level", "reason", "chat_file", "message_count"],
        "command_exec": ["ts", "level", "command", "args_summary", "elapsed_ms", "chat_file"],
        "command_error": ["ts", "level", "command", "args_summary", "error_type", "error", "chat_file"],
        "chat_opened": ["ts", "level", "action", "chat_file", "previous_chat_file", "message_count"],
        "chat_closed": ["ts", "level", "reason", "chat_file", "message_count"],
        "chat_renamed": ["ts", "level", "old_chat_file", "new_chat_file"],
        "chat_deleted": ["ts", "level", "reason", "chat_file"],
        "ai_request": [
            "ts", "level", "mode", "provider", "model", "chat_file",
            "message_count", "input_chars", "has_system_prompt", "system_prompt_path",
        ],
        "ai_response": [
            "ts", "level", "mode", "provider", "model", "chat_file",
            "latency_ms", "output_chars",
        ],
        "ai_error": [
            "ts", "level", "mode", "provider", "model", "chat_file",
            "latency_ms", "error_type", "error",
        ],
        "helper_ai_request": [
            "ts", "level", "task", "provider", "model",
            "message_count", "input_chars", "has_system_prompt",
        ],
        "helper_ai_response": [
            "ts", "level", "task", "provider", "model",
            "latency_ms", "output_chars",
        ],
        "helper_ai_error": [
            "ts", "level", "task", "provider", "model",
            "latency_ms", "error_type", "error",
        ],
        "provider_validation_error": [
            "ts", "level", "provider", "model", "phase",
            "chat_file", "error_type", "error",
        ],
        "log": ["ts", "level", "logger", "message"],
    }

    def _format_value(self, value: Any, max_len: int = 400) -> str:
        value_str = sanitize_error_message(str(value))
        if len(value_str) > max_len:
            value_str = value_str[: max_len - 3] + "..."
        return value_str.replace("\n", "\\n")

    def _ordered_keys(self, event_name: str, data: dict[str, Any]) -> list[str]:
        preferred = self.EVENT_KEY_ORDER.get(event_name, ["ts", "level", "logger"])
        preferred_present = [k for k in preferred if k in data and data[k] is not None]
        remaining = sorted(k for k in data.keys() if k not in preferred and data[k] is not None)
        return preferred_present + remaining

    def format(self, record: logging.LogRecord) -> str:
        base = {
            "ts": datetime.now().astimezone().isoformat(),
            "level": record.levelname,
            "logger": record.name,
        }

        message = record.getMessage()
        parsed = None
        if message.startswith("{") and message.endswith("}"):
            try:
                parsed = json.loads(message)
            except Exception:
                parsed = None

        if isinstance(parsed, dict):
            base.update(parsed)
        else:
            base["event"] = "log"
            base["message"] = sanitize_error_message(message)

        event_name = str(base.pop("event", "log"))
        lines = [f"=== {event_name} ==="]

        ordered_keys = self._ordered_keys(event_name, base)
        for key in ordered_keys:
            lines.append(f"{key}: {self._format_value(base[key])}")

        if record.exc_info:
            lines.append("traceback:")
            lines.append(self.formatException(record.exc_info))

        lines.append("--- end ---")
        return "\n".join(lines) + "\n"


def _to_log_safe(value: Any) -> Any:
    """Convert values to JSON-serializable, log-safe representations."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _to_log_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_log_safe(v) for v in value]
    return str(value)


def _summarize_text(text: Any, max_len: int = 160) -> str:
    """Return a short, redacted summary for logs."""
    if text is None:
        return ""
    normalized = " ".join(str(text).split())
    redacted = sanitize_error_message(normalized)
    if len(redacted) <= max_len:
        return redacted
    return redacted[: max_len - 3] + "..."


def _summarize_command_args(command: str, args: str) -> str:
    """Summarize command args while avoiding sensitive/free-form text leakage."""
    safe_preview_commands = {
        "open", "switch", "close", "new", "rename", "delete",
        "model", "helper", "timeout", "system", "history", "show", "safe",
        "input", "status", "title", "summary",
    }
    if not args.strip():
        return ""
    if command in safe_preview_commands:
        return _summarize_text(args, max_len=100)
    return "[redacted]"


def _estimate_message_chars(messages: list[dict]) -> int:
    """Estimate total character length across chat messages."""
    total = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, list):
            total += sum(len(str(part)) for part in content)
        else:
            total += len(str(content))
    return total


def _chat_file_label(chat_path: Optional[str]) -> Optional[str]:
    """Return a compact chat file label for logs."""
    if not chat_path:
        return None
    return Path(chat_path).name


def log_event(event: str, level: int = logging.INFO, **fields: Any) -> None:
    """Emit a structured log event as a single JSON line."""
    payload = {
        "ts": datetime.now().astimezone().isoformat(),
        "event": event,
    }
    for key, value in fields.items():
        payload[key] = _to_log_safe(value)
    logging.log(level, json.dumps(payload, ensure_ascii=False, separators=(",", ":")))


def _map_cli_path(path_value: Optional[str], arg_name: str) -> Optional[str]:
    """Map a CLI path argument using profile path mapping rules.

    Supports `~/...`, `@/...`, and absolute paths. Rejects plain relative paths.
    """
    if path_value is None:
        return None

    try:
        return profile.map_path(path_value)
    except ValueError as e:
        raise ValueError(f"Invalid {arg_name} path: {e}")


def sanitize_error_message(error_msg: str) -> str:
    """Sanitize error messages to remove sensitive information.

    Args:
        error_msg: Raw error message

    Returns:
        Sanitized error message with credentials redacted
    """
    # Redact common API key patterns (minimum 10 chars to catch various formats)
    sanitized = re.sub(r'sk-[A-Za-z0-9]{10,}', '[REDACTED_API_KEY]', error_msg)
    sanitized = re.sub(r'sk-ant-[A-Za-z0-9\-]{10,}', '[REDACTED_API_KEY]', sanitized)
    sanitized = re.sub(r'xai-[A-Za-z0-9]{10,}', '[REDACTED_API_KEY]', sanitized)
    sanitized = re.sub(r'pplx-[A-Za-z0-9]{10,}', '[REDACTED_API_KEY]', sanitized)

    # Redact potential tokens in Bearer headers
    sanitized = re.sub(r'Bearer\s+[A-Za-z0-9_\-\.]{20,}', 'Bearer [REDACTED_TOKEN]', sanitized)

    # Redact anything that looks like a JWT
    sanitized = re.sub(r'eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+', '[REDACTED_JWT]', sanitized)

    return sanitized


def _build_run_log_path(log_dir: str) -> str:
    """Build a unique run log path in the configured log directory."""
    log_dir_path = Path(log_dir)
    log_dir_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    base_name = f"poly-chat_{timestamp}"
    candidate = log_dir_path / f"{base_name}.log"

    suffix = 1
    while candidate.exists():
        candidate = log_dir_path / f"{base_name}_{suffix}.log"
        suffix += 1

    return str(candidate)


@dataclass
class SessionState:
    """Session state for the REPL loop."""

    current_ai: str
    current_model: str
    helper_ai: str
    helper_model: str
    profile: dict[str, Any]
    chat: dict[str, Any]
    system_prompt: Optional[str] = None
    system_prompt_path: Optional[str] = None
    input_mode: str = "quick"
    retry_mode: bool = False
    retry_base_messages: list = field(default_factory=list)
    retry_current_user_msg: Optional[str] = None
    retry_current_assistant_msg: Optional[str] = None
    secret_mode: bool = False
    secret_base_messages: list = field(default_factory=list)
    message_hex_ids: dict[int, str] = field(default_factory=dict)
    hex_id_set: set[str] = field(default_factory=set)
    _provider_cache: dict[tuple[str, str], ProviderInstance] = field(
        default_factory=dict
    )

    def get_cached_provider(
        self, provider_name: str, api_key: str
    ) -> Optional[ProviderInstance]:
        """Get cached provider instance if available."""
        return self._provider_cache.get((provider_name, api_key))

    def cache_provider(
        self, provider_name: str, api_key: str, instance: ProviderInstance
    ) -> None:
        """Cache a provider instance."""
        self._provider_cache[(provider_name, api_key)] = instance


def initialize_message_hex_ids(session: SessionState) -> None:
    """Initialize hex IDs for all messages in the current chat.

    Args:
        session: Session state with chat data

    This function assigns hex IDs to all existing messages and updates
    the session's hex ID tracking structures.
    """
    # Clear existing IDs
    session.message_hex_ids.clear()
    session.hex_id_set.clear()

    # Assign IDs to all messages
    if session.chat and "messages" in session.chat:
        message_count = len(session.chat["messages"])
        session.message_hex_ids = hex_id.assign_hex_ids(
            message_count, session.hex_id_set
        )


def assign_new_message_hex_id(session: SessionState, message_index: int) -> str:
    """Assign hex ID to a newly added message.

    Args:
        session: Session state
        message_index: Index of the new message

    Returns:
        The generated hex ID
    """
    new_hex_id = hex_id.generate_hex_id(session.hex_id_set)
    session.message_hex_ids[message_index] = new_hex_id
    return new_hex_id


def reset_chat_scoped_state(session: SessionState, session_dict: dict[str, Any]) -> None:
    """Reset state that should not leak across chat boundaries."""
    session.retry_mode = False
    session.retry_base_messages.clear()
    session.retry_current_user_msg = None
    session.retry_current_assistant_msg = None
    session_dict["retry_mode"] = False

    session.secret_mode = False
    session.secret_base_messages.clear()
    session_dict["secret_mode"] = False


def has_pending_error(chat_data: dict) -> bool:
    """Check if chat has a pending error that blocks normal conversation.

    Args:
        chat_data: Chat dictionary

    Returns:
        True if last message is an error, False otherwise
    """
    if not chat_data or "messages" not in chat_data:
        return False

    messages = chat_data["messages"]
    if not messages:
        return False

    last_msg = messages[-1]
    return last_msg.get("role") == "error"


def setup_logging(log_file: Optional[str] = None) -> None:
    """Set up logging configuration.

    Args:
        log_file: Path to log file, or None to disable logging
    """
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(str(log_path), encoding="utf-8")
        handler.setFormatter(StructuredTextFormatter())
        logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
    else:
        # Disable logging
        logging.disable(logging.CRITICAL)


def get_provider_instance(
    provider_name: str, api_key: str, session: Optional[SessionState] = None
) -> ProviderInstance:
    """Get AI provider instance, using cache if available.

    Args:
        provider_name: Name of provider (openai, claude, etc.)
        api_key: API key for provider
        session: Optional session state for caching

    Returns:
        Provider instance

    Raises:
        ValueError: If provider not supported
    """
    # Check cache first
    if session:
        cached = session.get_cached_provider(provider_name, api_key)
        if cached:
            return cached

    provider_class = PROVIDER_CLASSES.get(provider_name)
    if not provider_class:
        raise ValueError(f"Unsupported provider: {provider_name}")

    # Get timeout from profile (default 30)
    timeout = session.profile.get("timeout", 30) if session else 30

    instance = provider_class(api_key, timeout=timeout)

    # Cache the instance
    if session:
        session.cache_provider(provider_name, api_key, instance)

    return instance


async def send_message_to_ai(
    provider_instance: ProviderInstance,
    messages: list[dict],
    model: str,
    system_prompt: Optional[str] = None,
    provider_name: Optional[str] = None,
    mode: str = "normal",
    chat_path: Optional[str] = None,
) -> tuple[str, dict]:
    """Send message to AI and get response.

    Args:
        provider_instance: AI provider instance
        messages: Chat messages
        model: Model name
        system_prompt: Optional system prompt

    Returns:
        Tuple of (response_text, metadata)
    """
    provider_label = provider_name or provider_instance.__class__.__name__
    log_event(
        "ai_request",
        level=logging.INFO,
        mode=mode,
        provider=provider_label,
        model=model,
        chat_file=_chat_file_label(chat_path),
        message_count=len(messages),
        input_chars=_estimate_message_chars(messages),
        has_system_prompt=bool(system_prompt),
    )

    started = time.perf_counter()
    try:
        # Stream response
        response_stream = provider_instance.send_message(
            messages=messages, model=model, system_prompt=system_prompt, stream=True
        )

        # Display and accumulate
        response_text = await display_streaming_response(response_stream, prefix="")

        # Get metadata (token usage, etc.)
        # For now, return empty metadata as streaming doesn't provide it
        metadata = {"model": model}

        log_event(
            "ai_response",
            level=logging.INFO,
            mode=mode,
            provider=provider_label,
            model=model,
            chat_file=_chat_file_label(chat_path),
            latency_ms=round((time.perf_counter() - started) * 1000, 1),
            output_chars=len(response_text),
        )

        return response_text, metadata

    except Exception as e:
        log_event(
            "ai_error",
            level=logging.ERROR,
            mode=mode,
            provider=provider_label,
            model=model,
            chat_file=_chat_file_label(chat_path),
            latency_ms=round((time.perf_counter() - started) * 1000, 1),
            error_type=type(e).__name__,
            error=sanitize_error_message(str(e)),
        )
        logging.error(
            f"Error sending message to AI (provider={provider_label}, model={model}, mode={mode}): {e}",
            exc_info=True,
        )
        raise


def validate_and_get_provider(
    session: SessionState,
    chat_path: Optional[str] = None,
) -> tuple[Optional[ProviderInstance], Optional[str]]:
    """Validate API key and get provider instance.

    Args:
        session: Session state

    Returns:
        Tuple of (provider_instance, error_message)
        If successful, error_message is None
        If failed, provider_instance is None
    """
    provider_name = session.current_ai
    key_config = session.profile["api_keys"].get(provider_name)

    if not key_config:
        log_event(
            "provider_validation_error",
            level=logging.ERROR,
            provider=provider_name,
            model=session.current_model,
            phase="key_config_missing",
            chat_file=_chat_file_label(chat_path),
            error_type="ValueError",
            error=f"No API key configured for {provider_name}",
        )
        return None, f"No API key configured for {provider_name}"

    try:
        api_key = load_api_key(provider_name, key_config)
    except Exception as e:
        sanitized = sanitize_error_message(str(e))
        log_event(
            "provider_validation_error",
            level=logging.ERROR,
            provider=provider_name,
            model=session.current_model,
            phase="key_load_failed",
            chat_file=_chat_file_label(chat_path),
            error_type=type(e).__name__,
            error=sanitized,
        )
        logging.error(f"API key loading error: {e}", exc_info=True)
        return None, f"Error loading API key: {e}"

    if not validate_api_key(api_key, provider_name):
        log_event(
            "provider_validation_error",
            level=logging.ERROR,
            provider=provider_name,
            model=session.current_model,
            phase="key_validation_failed",
            chat_file=_chat_file_label(chat_path),
            error_type="ValueError",
            error=f"Invalid API key for {provider_name}",
        )
        return None, f"Invalid API key for {provider_name}"

    try:
        provider_instance = get_provider_instance(provider_name, api_key, session)
    except Exception as e:
        sanitized = sanitize_error_message(str(e))
        log_event(
            "provider_validation_error",
            level=logging.ERROR,
            provider=provider_name,
            model=session.current_model,
            phase="provider_init_failed",
            chat_file=_chat_file_label(chat_path),
            error_type=type(e).__name__,
            error=sanitized,
        )
        logging.error(f"Provider initialization error: {e}", exc_info=True)
        return None, f"Error initializing provider: {e}"

    return provider_instance, None


async def repl_loop(
    profile_data: dict,
    chat_data: Optional[dict] = None,
    chat_path: Optional[str] = None,
    system_prompt: Optional[str] = None,
    system_prompt_path: Optional[str] = None,
    profile_path: Optional[str] = None,
    log_file: Optional[str] = None,
) -> None:
    """Run the REPL loop.

    Args:
        profile_data: Loaded profile
        chat_data: Loaded chat history (optional)
        chat_path: Path to chat history file (optional)
        system_prompt: Optional system prompt text
        system_prompt_path: Optional path to system prompt (for metadata)
        profile_path: Absolute profile path for status display
        log_file: Effective log file path for this run
    """
    # Determine helper AI (defaults to default_ai if not specified)
    helper_ai_name = profile_data.get("default_helper_ai", profile_data["default_ai"])
    helper_model_name = profile_data["models"][helper_ai_name]
    input_mode = profile_data.get("input_mode", "quick")
    if input_mode not in ("quick", "compose"):
        input_mode = "quick"

    # Initialize session state (chat can be None)
    session = SessionState(
        current_ai=profile_data["default_ai"],
        current_model=profile_data["models"][profile_data["default_ai"]],
        helper_ai=helper_ai_name,
        helper_model=helper_model_name,
        profile=profile_data,
        chat=chat_data if chat_data else {},
        system_prompt=system_prompt,
        system_prompt_path=system_prompt_path,
        input_mode=input_mode,
    )

    # Set system_prompt_path in chat metadata if chat is loaded
    if chat_data and system_prompt_path and not chat_data["metadata"].get("system_prompt_path"):
        chat.update_metadata(
            chat_data, system_prompt_path=system_prompt_path
        )

    # Initialize hex IDs for loaded chat
    if chat_data:
        initialize_message_hex_ids(session)

    # Initialize command handler (pass session as dict for compatibility)
    session_dict = {
        "current_ai": session.current_ai,
        "current_model": session.current_model,
        "helper_ai": session.helper_ai,
        "helper_model": session.helper_model,
        "profile": session.profile,
        "profile_path": profile_path,
        "chat": session.chat,
        "chat_path": chat_path,
        "log_file": log_file,
        "system_prompt": session.system_prompt,
        "system_prompt_path": session.system_prompt_path,
        "input_mode": session.input_mode,
        "retry_mode": session.retry_mode,
        "secret_mode": session.secret_mode,
        "message_hex_ids": session.message_hex_ids,
        "hex_id_set": session.hex_id_set,
    }
    cmd_handler = CommandHandler(session_dict)
    chat_metadata = session.chat.get("metadata", {}) if isinstance(session.chat, dict) else {}
    log_event(
        "session_start",
        level=logging.INFO,
        profile_file=profile_path,
        chat_file=chat_path,
        log_file=log_file,
        chats_dir=session.profile.get("chats_dir"),
        log_dir=session.profile.get("log_dir"),
        assistant_provider=session.current_ai,
        assistant_model=session.current_model,
        helper_provider=session.helper_ai,
        helper_model=session.helper_model,
        input_mode=session.input_mode,
        timeout=session.profile.get("timeout", 30),
        system_prompt_path=session.system_prompt_path,
        chat_title=chat_metadata.get("title"),
        chat_summary=chat_metadata.get("summary"),
        message_count=len(session.chat.get("messages", [])) if isinstance(session.chat, dict) else 0,
    )

    # Set up key bindings for message submission
    kb = KeyBindings()

    @kb.add('enter', eager=True)
    def _(event):
        """Handle Enter based on input mode."""
        mode = session_dict.get("input_mode", "quick")
        if mode == "quick":
            # In quick mode, Enter submits unless buffer is empty/whitespace
            buffer_text = event.current_buffer.text
            if buffer_text and buffer_text.strip():
                # Has non-whitespace content, submit normally
                event.current_buffer.validate_and_handle()
            elif buffer_text and not buffer_text.strip():
                # Has only whitespace, clear buffer and ignore
                event.current_buffer.reset()
            # else: empty buffer, do nothing (ignore the Enter press)
        else:
            event.current_buffer.insert_text("\n")

    @kb.add('escape', 'enter', eager=True)  # Alt/Option+Enter (Meta+Enter)
    def _(event):
        """Handle Alt/Option+Enter based on input mode."""
        mode = session_dict.get("input_mode", "quick")
        if mode == "quick":
            event.current_buffer.insert_text("\n")
        else:
            event.current_buffer.validate_and_handle()

    @kb.add('c-j', eager=True)  # Ctrl+J (sent by Ctrl+Enter in many terminals)
    def _(event):
        """Submit message on Ctrl+J in any mode."""
        event.current_buffer.validate_and_handle()

    # Set up prompt_toolkit session with history and key bindings
    history_file = Path.home() / ".poly-chat-history"

    prompt_session = PromptSession(
        history=FileHistory(str(history_file)),
        key_bindings=kb,
        multiline=True,
    )

    # Get list of configured AI providers
    configured_ais = []
    for provider, model in profile_data["models"].items():
        if provider in profile_data.get("api_keys", {}):
            configured_ais.append(f"{provider} ({model})")

    # Display welcome message
    print("=" * 70)
    print("PolyChat - Multi-AI CLI Chat Tool")
    print("=" * 70)
    print(f"Current Provider: {session.current_ai}")
    print(f"Current Model:    {session.current_model}")
    print(f"Configured AIs:   {', '.join(configured_ais)}")
    if chat_path:
        print(f"Chat:             {Path(chat_path).name}")
    else:
        print("Chat:             None (use /new or /open)")
    print()
    if session.input_mode == "quick":
        print("Input Mode:       quick (Enter sends • Option/Alt+Enter inserts new line)")
    else:
        print("Input Mode:       compose (Enter inserts new line • Option/Alt+Enter sends)")
    print("Ctrl+J also sends in both modes")
    print("Type /help for commands • Ctrl+D to exit")
    print("=" * 70)
    print()

    # Main REPL loop
    while True:
        try:
            # Display mode indicators
            if has_pending_error(chat_data) and not session.retry_mode:
                print("[⚠️  PENDING ERROR - Use /retry to retry or /secret to ask separately]")
            elif session.retry_mode:
                print("[🔄 RETRY MODE - Use /apply to accept, /cancel to abort]")
            elif session.secret_mode:
                print("[🔒 SECRET MODE - Messages not saved to history]")

            # Get user input (multiline)
            user_input = await prompt_session.prompt_async(
                '',  # Empty prompt
                multiline=True,
                prompt_continuation=lambda width, line_number, is_soft_wrap: ''
            )

            if not user_input.strip():
                continue

            # Check if it's a command
            if cmd_handler.is_command(user_input):
                try:
                    command_name, command_args = cmd_handler.parse_command(user_input)
                    command_started = time.perf_counter()
                    response = await cmd_handler.execute_command(user_input)
                    log_event(
                        "command_exec",
                        level=logging.INFO,
                        command=command_name,
                        args_summary=_summarize_command_args(command_name, command_args),
                        elapsed_ms=round((time.perf_counter() - command_started) * 1000, 1),
                        chat_file=chat_path,
                    )

                    # Handle special command signals
                    if response == "__EXIT__":
                        log_event(
                            "session_stop",
                            level=logging.INFO,
                            reason="exit_command",
                            chat_file=chat_path,
                            message_count=len(chat_data.get("messages", [])) if chat_data else 0,
                        )
                        print("\nGoodbye!")
                        break

                    elif response.startswith("__NEW_CHAT__:"):
                        # Create new chat
                        new_path = response.split(":", 1)[1]
                        previous_chat = chat_path
                        chat_path = new_path
                        chat_data = chat.load_chat(chat_path)

                        # Set system_prompt_path if configured
                        if system_prompt_path:
                            chat.update_metadata(chat_data, system_prompt_path=system_prompt_path)

                        # Update session
                        session.chat = chat_data
                        session_dict["chat"] = chat_data
                        session_dict["chat_path"] = chat_path

                        # Initialize hex IDs
                        initialize_message_hex_ids(session)
                        reset_chat_scoped_state(session, session_dict)
                        log_event(
                            "chat_opened",
                            level=logging.INFO,
                            action="new",
                            chat_file=chat_path,
                            previous_chat_file=previous_chat,
                            message_count=len(chat_data.get("messages", [])),
                        )

                        print(f"Created new chat: {Path(chat_path).name}")
                        print()

                    elif response.startswith("__OPEN_CHAT__:"):
                        # Open existing chat
                        new_path = response.split(":", 1)[1]
                        previous_chat = chat_path

                        # Save current chat if any
                        if chat_path and chat_data:
                            await chat.save_chat(chat_path, chat_data)

                        # Load new chat
                        chat_path = new_path
                        chat_data = chat.load_chat(chat_path)

                        # Update session
                        session.chat = chat_data
                        session_dict["chat"] = chat_data
                        session_dict["chat_path"] = chat_path

                        # Initialize hex IDs
                        initialize_message_hex_ids(session)
                        reset_chat_scoped_state(session, session_dict)
                        log_event(
                            "chat_opened",
                            level=logging.INFO,
                            action="open",
                            chat_file=chat_path,
                            previous_chat_file=previous_chat,
                            message_count=len(chat_data.get("messages", [])),
                        )

                        print(f"Opened chat: {Path(chat_path).name}")
                        print()

                    elif response == "__CLOSE_CHAT__":
                        # Save and close current chat
                        closed_chat = chat_path
                        closed_count = len(chat_data.get("messages", [])) if chat_data else 0
                        if chat_path and chat_data:
                            await chat.save_chat(chat_path, chat_data)

                        chat_path = None
                        chat_data = None

                        # Update session
                        session.chat = {}
                        session_dict["chat"] = {}
                        session_dict["chat_path"] = None

                        # Clear hex IDs
                        session.message_hex_ids.clear()
                        session.hex_id_set.clear()
                        reset_chat_scoped_state(session, session_dict)
                        log_event(
                            "chat_closed",
                            level=logging.INFO,
                            reason="close_command",
                            chat_file=closed_chat,
                            message_count=closed_count,
                        )

                        print("Chat closed")
                        print()

                    elif response.startswith("__RENAME_CURRENT__:"):
                        # Update current chat path
                        new_path = response.split(":", 1)[1]
                        old_path = chat_path
                        chat_path = new_path
                        session_dict["chat_path"] = chat_path
                        log_event(
                            "chat_renamed",
                            level=logging.INFO,
                            old_chat_file=old_path,
                            new_chat_file=chat_path,
                        )

                        print(f"Chat renamed to: {Path(chat_path).name}")
                        print()

                    elif response.startswith("__DELETE_CURRENT__:"):
                        # Close current chat after deletion
                        filename = response.split(":", 1)[1]
                        deleted_chat = chat_path
                        chat_path = None
                        chat_data = None

                        # Update session
                        session.chat = {}
                        session_dict["chat"] = {}
                        session_dict["chat_path"] = None

                        # Clear hex IDs
                        session.message_hex_ids.clear()
                        session.hex_id_set.clear()
                        reset_chat_scoped_state(session, session_dict)
                        log_event(
                            "chat_deleted",
                            level=logging.INFO,
                            reason="delete_current",
                            chat_file=deleted_chat or filename,
                        )

                        print(f"Deleted and closed chat: {filename}")
                        print()

                    elif response == "__APPLY_RETRY__":
                        # Apply current retry attempt
                        if session.retry_current_user_msg and session.retry_current_assistant_msg:
                            # Delete last 2 messages (original user and assistant)
                            if len(chat_data["messages"]) >= 2:
                                # Remove last 2 messages
                                for _ in range(2):
                                    last_index = len(chat_data["messages"]) - 1
                                    chat_data["messages"].pop()
                                    # Remove hex ID
                                    if last_index in session.message_hex_ids:
                                        hex_to_remove = session.message_hex_ids.pop(last_index)
                                        session.hex_id_set.discard(hex_to_remove)

                            # Add retry attempt messages
                            chat.add_user_message(chat_data, session.retry_current_user_msg)
                            new_msg_index = len(chat_data["messages"]) - 1
                            assign_new_message_hex_id(session, new_msg_index)

                            chat.add_assistant_message(
                                chat_data, session.retry_current_assistant_msg, session.current_model
                            )
                            new_msg_index = len(chat_data["messages"]) - 1
                            assign_new_message_hex_id(session, new_msg_index)

                            # Save chat
                            await chat.save_chat(chat_path, chat_data)

                        # Clear retry state
                        session.retry_mode = False
                        session.retry_base_messages.clear()
                        session.retry_current_user_msg = None
                        session.retry_current_assistant_msg = None
                        session_dict["retry_mode"] = False

                        print("Retry applied. Original message replaced.")
                        print()

                    elif response == "__CANCEL_RETRY__":
                        # Clear retry state without modifying chat
                        session.retry_mode = False
                        session.retry_base_messages.clear()
                        session.retry_current_user_msg = None
                        session.retry_current_assistant_msg = None
                        session_dict["retry_mode"] = False

                        print("Retry cancelled. Original message kept.")
                        print()

                    elif response == "__CLEAR_SECRET_CONTEXT__":
                        # Clear frozen secret context
                        session.secret_base_messages.clear()
                        print("Secret mode disabled. Messages will be saved normally.")
                        print()

                    elif response.startswith("__SECRET_ONESHOT__:"):
                        # Handle one-shot secret message
                        secret_message = response.split(":", 1)[1]

                        # Validate provider
                        provider_instance, error = validate_and_get_provider(session)
                        if error:
                            print(f"Error: {error}")
                            print()
                            continue

                        # Get current messages (frozen context)
                        messages = chat.get_messages_for_ai(chat_data)

                        # Add secret user message to context (temporarily, not to chat)
                        temp_messages = messages + [{
                            "role": "user",
                            "content": secret_message
                        }]

                        # Send to AI
                        try:
                            print(f"\n{session.current_ai.capitalize()} (secret): ", end="", flush=True)
                            response_text, metadata = await send_message_to_ai(
                                provider_instance,
                                temp_messages,
                                session.current_model,
                                session.system_prompt,
                                provider_name=session.current_ai,
                                mode="secret_oneshot",
                                chat_path=chat_path,
                            )
                            print()
                            print()
                        except Exception as e:
                            print(f"\nError: {e}")
                            print()

                        continue

                    elif response:
                        print(response)
                        print()

                    # Sync session state back from command handler
                    session.current_ai = session_dict["current_ai"]
                    session.current_model = session_dict["current_model"]
                    session.helper_ai = session_dict.get("helper_ai", session.helper_ai)
                    session.helper_model = session_dict.get("helper_model", session.helper_model)
                    session.input_mode = session_dict.get("input_mode", session.input_mode)
                    session.retry_mode = session_dict.get("retry_mode", False)
                    session.secret_mode = session_dict.get("secret_mode", False)

                except ValueError as e:
                    command_name, command_args = cmd_handler.parse_command(user_input)
                    log_event(
                        "command_error",
                        level=logging.ERROR,
                        command=command_name,
                        args_summary=_summarize_command_args(command_name, command_args),
                        error_type=type(e).__name__,
                        error=sanitize_error_message(str(e)),
                        chat_file=chat_path,
                    )
                    print(f"Error: {e}")
                    print()
                continue

            # Check if chat is loaded
            if not chat_path:
                print("\nNo chat is currently open.")
                print("Use /new to create a new chat or /open to open an existing one.")
                print()
                continue

            # Check for pending error - block normal chat
            if has_pending_error(chat_data):
                print("\n⚠️  Cannot continue - last interaction resulted in an error.")
                print("Use /retry to retry the last message, /secret to ask without saving,")
                print("or /rewind to remove the error and continue from an earlier point.")
                print()
                continue

            # Validate provider BEFORE adding user message
            provider_instance, error = validate_and_get_provider(session, chat_path=chat_path)
            if error:
                print(f"Error: {error}")
                print()
                continue

            # Handle secret mode
            if session.secret_mode:
                # Freeze context if not already frozen
                if not session.secret_base_messages:
                    session.secret_base_messages = chat.get_messages_for_ai(chat_data).copy()

                # Build temporary messages with secret question
                temp_messages = session.secret_base_messages + [{
                    "role": "user",
                    "content": user_input
                }]

                # Send to AI (don't save anything)
                try:
                    print(f"\n{session.current_ai.capitalize()} (secret): ", end="", flush=True)
                    response_text, metadata = await send_message_to_ai(
                        provider_instance,
                        temp_messages,
                        session.current_model,
                        session.system_prompt,
                        provider_name=session.current_ai,
                        mode="secret",
                        chat_path=chat_path,
                    )
                    print()
                    print()
                except Exception as e:
                    print(f"\nError: {e}")
                    print()

                continue

            # Handle retry mode
            if session.retry_mode:
                # Freeze context if not already frozen (all messages except last assistant/error)
                if not session.retry_base_messages:
                    all_messages = chat.get_messages_for_ai(chat_data)
                    # Remove last message if it's assistant (normal retry) or skip errors (get_messages_for_ai excludes errors)
                    if all_messages and all_messages[-1]["role"] == "assistant":
                        session.retry_base_messages = all_messages[:-1].copy()
                    else:
                        session.retry_base_messages = all_messages.copy()

                # Store user message temporarily
                session.retry_current_user_msg = user_input

                # Build temporary messages with retry attempt
                temp_messages = session.retry_base_messages + [{
                    "role": "user",
                    "content": user_input
                }]

                # Send to AI (don't save to chat)
                try:
                    print(f"\n{session.current_ai.capitalize()} (retry): ", end="", flush=True)
                    response_text, metadata = await send_message_to_ai(
                        provider_instance,
                        temp_messages,
                        session.current_model,
                        session.system_prompt,
                        provider_name=session.current_ai,
                        mode="retry",
                        chat_path=chat_path,
                    )

                    # Store response temporarily
                    session.retry_current_assistant_msg = response_text

                    print()
                    print()
                except Exception as e:
                    print(f"\nError: {e}")
                    print()

                continue

            # NOW add user message (after validation passed)
            chat.add_user_message(chat_data, user_input)
            # Assign hex ID to new user message
            new_msg_index = len(chat_data["messages"]) - 1
            assign_new_message_hex_id(session, new_msg_index)

            # Get messages for AI
            messages = chat.get_messages_for_ai(chat_data)

            # Send to AI
            try:
                print(f"\n{session.current_ai.capitalize()}: ", end="", flush=True)
                response_text, metadata = await send_message_to_ai(
                    provider_instance,
                    messages,
                    session.current_model,
                    session.system_prompt,
                    provider_name=session.current_ai,
                    mode="normal",
                    chat_path=chat_path,
                )

                # Add assistant response to chat
                actual_model = metadata.get("model", session.current_model)
                chat.add_assistant_message(
                    chat_data, response_text, actual_model
                )
                # Assign hex ID to new assistant message
                new_msg_index = len(chat_data["messages"]) - 1
                assign_new_message_hex_id(session, new_msg_index)

                # Save chat history
                await chat.save_chat(
                    chat_path, chat_data
                )

                # Display token usage if available
                if "usage" in metadata:
                    usage = metadata["usage"]
                    print(f"\n[Tokens: {usage.get('total_tokens', 'N/A')}]")

                print()

            except KeyboardInterrupt:
                print("\n[Message cancelled]")
                # Remove the user message since we didn't get a response
                if (
                    chat_data["messages"]
                    and chat_data["messages"][-1]["role"] == "user"
                ):
                    last_index = len(chat_data["messages"]) - 1
                    chat_data["messages"].pop()
                    # Remove hex ID for popped message
                    if last_index in session.message_hex_ids:
                        hex_to_remove = session.message_hex_ids.pop(last_index)
                        session.hex_id_set.discard(hex_to_remove)
                print()
                continue

            except Exception as e:
                print(f"\nError: {e}")

                # Remove user message and add error instead
                if (
                    chat_data["messages"]
                    and chat_data["messages"][-1]["role"] == "user"
                ):
                    last_index = len(chat_data["messages"]) - 1
                    chat_data["messages"].pop()
                    # Remove hex ID for popped message
                    if last_index in session.message_hex_ids:
                        hex_to_remove = session.message_hex_ids.pop(last_index)
                        session.hex_id_set.discard(hex_to_remove)

                # Add error message to chat (sanitized to remove credentials)
                sanitized_error = sanitize_error_message(str(e))
                chat.add_error_message(
                    chat_data,
                    sanitized_error,
                    {"provider": session.current_ai, "model": session.current_model},
                )
                # Assign hex ID to new error message
                new_msg_index = len(chat_data["messages"]) - 1
                assign_new_message_hex_id(session, new_msg_index)

                # Save chat history with error
                await chat.save_chat(
                    chat_path, chat_data
                )
                print()

        except (EOFError, KeyboardInterrupt):
            # Ctrl-D or Ctrl-C at prompt
            log_event(
                "session_stop",
                level=logging.INFO,
                reason="keyboard_interrupt_or_eof",
                chat_file=chat_path,
                message_count=len(chat_data.get("messages", [])) if chat_data else 0,
            )
            print("\nGoodbye!")
            break


def main() -> None:
    """Main entry point for PolyChat CLI."""
    parser = argparse.ArgumentParser(
        description="PolyChat - Multi-AI CLI Chat Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-p", "--profile", help="Path to profile file (required for normal mode)"
    )

    parser.add_argument(
        "-c",
        "--chat",
        help="Path to chat history file (optional, will prompt if not provided)",
    )

    parser.add_argument(
        "-l", "--log", help="Path to log file for error logging (optional)"
    )

    parser.add_argument(
        "command", nargs="?", help="Command to run (e.g., 'init' to create profile)"
    )

    parser.add_argument(
        "profile_path", nargs="?", help="Profile path (for init command)"
    )

    args = parser.parse_args()
    app_started = time.perf_counter()

    # Handle 'init' command for profile creation
    if args.command == "init":
        if not args.profile_path:
            print("Error: profile path required for init command")
            print("Usage: pc init <profile-path>")
            sys.exit(1)
        try:
            mapped_init_profile_path = _map_cli_path(args.profile_path, "profile")
            profile.create_profile(mapped_init_profile_path)
            sys.exit(0)
        except Exception as e:
            print(f"Error creating profile: {e}")
            sys.exit(1)

    # For normal mode, -p is required
    if not args.profile:
        print("Error: -p/--profile is required")
        print("Usage: pc -p <profile-path> [-c <chat-path>] [-l <log-path>]")
        sys.exit(1)

    try:
        # Map CLI paths using shared path mapping rules
        mapped_profile_path = _map_cli_path(args.profile, "profile")
        mapped_chat_path = _map_cli_path(args.chat, "chat")
        mapped_log_path = _map_cli_path(args.log, "log")

        # Load profile
        profile_data = profile.load_profile(mapped_profile_path)

        # Set up logging. If no CLI log path was provided, create a run log in profile log_dir.
        effective_log_path = mapped_log_path or _build_run_log_path(profile_data["log_dir"])
        setup_logging(effective_log_path)

        # Get chat history file path (optional)
        chat_path = None
        chat_data = None

        if mapped_chat_path:
            # Map the path and load chat
            chat_path = mapped_chat_path
            chat_data = chat.load_chat(chat_path)

        # Load system prompt if configured
        system_prompt = None
        system_prompt_path = None
        if isinstance(profile_data.get("system_prompt"), str):
            # Read original profile to get unmapped path for system_prompt_path
            # (profile_data has already mapped paths, but we want to preserve original format)
            try:
                with open(mapped_profile_path, "r", encoding="utf-8") as f:
                    original_profile = json.load(f)
                    system_prompt_path = original_profile.get("system_prompt")
            except Exception:
                # Fallback to mapped path if can't read original
                system_prompt_path = profile_data["system_prompt"]

            # Load the actual prompt content using mapped path
            try:
                system_prompt_mapped_path = profile.map_system_prompt_path(system_prompt_path)
                with open(system_prompt_mapped_path, "r", encoding="utf-8") as f:
                    system_prompt = f.read().strip()
            except Exception as e:
                print(f"Warning: Could not load system prompt: {e}")
        elif isinstance(profile_data.get("system_prompt"), dict):
            # It's inline text
            system_prompt = profile_data["system_prompt"].get("content")

        log_event(
            "app_start",
            level=logging.INFO,
            profile_file=mapped_profile_path,
            chat_file=mapped_chat_path,
            log_file=effective_log_path,
            chats_dir=profile_data.get("chats_dir"),
            log_dir=profile_data.get("log_dir"),
            assistant_provider=profile_data.get("default_ai"),
            assistant_model=profile_data.get("models", {}).get(profile_data.get("default_ai", ""), "(unknown)"),
            helper_provider=profile_data.get("default_helper_ai", profile_data.get("default_ai")),
            helper_model=profile_data.get("models", {}).get(
                profile_data.get("default_helper_ai", profile_data.get("default_ai", "")),
                "(unknown)",
            ),
            input_mode=profile_data.get("input_mode", "quick"),
            timeout=profile_data.get("timeout", 30),
            system_prompt_path=system_prompt_path,
        )

        # Run REPL loop
        asyncio.run(
            repl_loop(
                profile_data,
                chat_data,
                chat_path,
                system_prompt,
                system_prompt_path,
                mapped_profile_path,
                effective_log_path,
            )
        )
        log_event(
            "app_stop",
            level=logging.INFO,
            reason="normal",
            uptime_ms=round((time.perf_counter() - app_started) * 1000, 1),
        )

    except KeyboardInterrupt:
        log_event(
            "app_stop",
            level=logging.INFO,
            reason="keyboard_interrupt",
            uptime_ms=round((time.perf_counter() - app_started) * 1000, 1),
        )
        print("\nInterrupted")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        log_event(
            "app_stop",
            level=logging.ERROR,
            reason="fatal_error",
            error_type=type(e).__name__,
            error=sanitize_error_message(str(e)),
            uptime_ms=round((time.perf_counter() - app_started) * 1000, 1),
        )
        logging.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
