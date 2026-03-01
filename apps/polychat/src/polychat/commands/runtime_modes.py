"""Runtime mode command handlers and compatibility adapters."""

from typing import TYPE_CHECKING

from .. import chat, hex_id, profile
from ..ai.capabilities import SEARCH_SUPPORTED_PROVIDERS, provider_supports_search
from ..chat import resolve_last_interaction_span, update_metadata
from .types import CommandResult, CommandSignal

if TYPE_CHECKING:
    from .contracts import CommandDependencies as _CommandDependencies
else:
    class _CommandDependencies:
        pass


class RuntimeModeCommandHandlers:
    """Explicit handlers for runtime mode and prompt commands."""

    def __init__(self, dependencies: _CommandDependencies) -> None:
        self._deps = dependencies

    async def set_input_mode(self, args: str) -> str:
        """Set or show input mode.

        Modes:
            quick: Enter sends, Alt/Option+Enter inserts newline
            compose: Enter inserts newline, Alt/Option+Enter sends
        """
        current_mode = self._deps.manager.input_mode

        if not args:
            if current_mode == "quick":
                return "Input mode: quick (Enter sends, Alt/Option+Enter inserts newline)"
            return "Input mode: compose (Enter inserts newline, Alt/Option+Enter sends)"

        value = args.strip().lower()

        if value == "default":
            profile_mode = self._deps.manager.profile.input_mode
            if profile_mode not in ("quick", "compose"):
                profile_mode = "quick"
            self._deps.manager.input_mode = profile_mode
            if profile_mode == "quick":
                return "Input mode restored to profile default: quick"
            return "Input mode restored to profile default: compose"

        if value in ("quick", "compose"):
            self._deps.manager.input_mode = value
            if value == "quick":
                return "Input mode set to quick (Enter sends)"
            return "Input mode set to compose (Enter inserts newline)"

        raise ValueError("Invalid input mode. Use /input quick, /input compose, or /input default.")

    async def set_system_prompt(self, args: str) -> str:
        """Set or show system prompt path for current chat session.

        Args:
            args: Path to system prompt file, '--' to remove, 'default' to restore,
                  persona (e.g., 'razor', 'socrates'), or empty to show

        Returns:
            Confirmation message
        """
        chat_data = self._deps._require_open_chat(need_metadata=True)
        if chat_data is None:
            return "No chat is currently open"

        if not args:
            current_path = (
                chat_data.metadata.system_prompt
                or self._deps.manager.system_prompt_path
            )
            if current_path:
                return f"Current system prompt: {current_path}"
            return "No system prompt set for this chat"

        if args == "--":
            update_metadata(chat_data, system_prompt=None)
            self._deps.manager.system_prompt = None
            self._deps.manager.system_prompt_path = None

            return "System prompt removed from chat"

        if args == "default":
            if not self._deps.manager.profile.system_prompt:
                return "No default system prompt configured in profile"

            (
                system_prompt_content,
                system_prompt_path,
                warning,
            ) = self._deps.manager.load_system_prompt(
                self._deps.manager.profile,
                self._deps.manager.profile_path,
                strict=True,
            )
            if warning:
                raise ValueError(warning)

            update_metadata(chat_data, system_prompt=system_prompt_path)

            self._deps.manager.system_prompt = system_prompt_content
            self._deps.manager.system_prompt_path = system_prompt_path

            if system_prompt_path is None and system_prompt_content:
                return "System prompt restored to inline profile default (content hidden)"
            return "System prompt restored to profile default"

        if "/" not in args and not args.startswith("@") and not args.startswith("~"):
            persona_path = f"@/prompts/system/{args}.txt"
            try:
                mapped_path = profile.map_system_prompt_path(persona_path)
                if mapped_path is None:
                    raise ValueError("Unknown persona")
                with open(mapped_path, "r", encoding="utf-8") as file:
                    system_prompt_content = file.read().strip()

                update_metadata(chat_data, system_prompt=persona_path)
                self._deps.manager.system_prompt = system_prompt_content
                self._deps.manager.system_prompt_path = persona_path

                return f"System prompt set to: {args} persona"
            except (ValueError, FileNotFoundError, OSError):
                raise ValueError(f"Unknown persona: {args}")

        try:
            system_prompt_mapped_path = profile.map_system_prompt_path(args)
            if system_prompt_mapped_path is None:
                raise ValueError("System prompt path is required")

            try:
                with open(system_prompt_mapped_path, "r", encoding="utf-8") as file:
                    system_prompt_content = file.read().strip()
            except FileNotFoundError:
                raise ValueError(f"System prompt file not found: {system_prompt_mapped_path}")
            except Exception:
                raise ValueError(f"Could not read system prompt file: {system_prompt_mapped_path}")

            update_metadata(chat_data, system_prompt=args)

            self._deps.manager.system_prompt = system_prompt_content
            self._deps.manager.system_prompt_path = args

            return f"System prompt set to: {args}"

        except ValueError:
            raise

    async def retry_mode(self, args: str) -> str:
        """Enter retry mode to replace the last interaction from prior context."""
        chat_data = self._deps.manager.chat

        if not chat_data.messages and not self._deps.manager.chat_path:
            return "No chat is currently open"

        messages = chat_data.messages

        if not messages:
            return "No messages to retry"

        interaction_span = resolve_last_interaction_span(messages)
        if interaction_span is None:
            return "Last message is not an assistant response or error. Nothing to retry."

        retry_context = chat.get_retry_context_for_last_interaction(chat_data)
        self._deps.manager.retry.enter(
            retry_context,
            target_span=interaction_span,
        )
        return "Retry mode enabled"

    async def apply_retry(self, args: str) -> CommandResult:
        """Apply current retry attempt and exit retry mode."""
        if not self._deps.manager.retry.active:
            return "Not in retry mode"

        normalized_args = args.strip().lower()
        if normalized_args in {"", "last"}:
            retry_hex_id = self._deps.manager.retry.latest_attempt_id()
            if not retry_hex_id:
                return "No retry attempts available yet"
            return CommandSignal(kind="apply_retry", value=retry_hex_id)

        retry_hex_id = normalized_args
        if not hex_id.is_hex_id(retry_hex_id):
            return f"Invalid hex ID: {args.strip()}"

        return CommandSignal(kind="apply_retry", value=retry_hex_id)

    async def cancel_retry(self, args: str) -> CommandResult:
        """Cancel retry mode and keep original messages."""
        if not self._deps.manager.retry.active:
            return "Not in retry mode"

        return CommandSignal(kind="cancel_retry")

    async def secret_mode_command(self, args: str) -> str:
        """Show or set secret mode (temporary off-record continuation branch)."""
        chat_data = self._deps.manager.chat

        if not chat_data.messages and not self._deps.manager.chat_path:
            return "No chat is currently open"

        normalized = args.strip().lower()

        if not normalized:
            return "Secret mode: on" if self._deps.manager.secret.active else "Secret mode: off"

        if normalized == "on":
            if self._deps.manager.secret.active:
                return "Secret mode already on"
            secret_context = chat.get_messages_for_ai(chat_data)
            self._deps.manager.secret.enter(secret_context)
            return "Secret mode enabled"

        if normalized == "off":
            if self._deps.manager.secret.active:
                self._deps.manager.secret.exit()
                return "Secret mode disabled"
            return "Secret mode already off"

        if normalized in {"on/off", "on|off"}:
            return "Use /secret on or /secret off"

        raise ValueError("Invalid argument. Use /secret on or /secret off")

    async def search_mode_command(self, args: str) -> str:
        """Show or set search mode (web search enabled)."""
        chat_data = self._deps.manager.chat

        if not chat_data.messages and not self._deps.manager.chat_path:
            return "No chat is currently open"

        normalized = args.strip().lower()

        if not normalized:
            status = "on" if self._deps.manager.search_mode else "off"
            providers = ", ".join(sorted(SEARCH_SUPPORTED_PROVIDERS))
            return f"Search mode: {status}\nSupported providers: {providers}"

        if normalized == "on":
            if not provider_supports_search(self._deps.manager.current_ai):
                providers = ", ".join(sorted(SEARCH_SUPPORTED_PROVIDERS))
                return f"Search not supported for {self._deps.manager.current_ai}. Supported: {providers}"
            if self._deps.manager.search_mode:
                return "Search mode already on"
            self._deps.manager.search_mode = True
            return "Search mode enabled"

        if normalized == "off":
            if self._deps.manager.search_mode:
                self._deps.manager.search_mode = False
                return "Search mode disabled"
            return "Search mode already off"

        if normalized in {"on/off", "on|off"}:
            return "Use /search on or /search off"

        raise ValueError("Invalid argument. Use /search on or /search off")
