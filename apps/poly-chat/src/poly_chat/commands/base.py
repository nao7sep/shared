"""Base command handler mixin for shared session/path helpers."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING

from .. import models
from ..path_mapping import map_path
from ..chat import update_metadata
from ..ui.interaction import ThreadedConsoleInteraction, UserInteractionPort

if TYPE_CHECKING:
    from ..session_manager import SessionManager


class CommandHandlerBaseMixin:
    def __init__(
        self,
        manager: "SessionManager",
        interaction: Optional[UserInteractionPort] = None,
    ):
        """Initialize command handler.

        Args:
            manager: SessionManager instance for unified state access
        """
        self.manager = manager
        self.interaction = interaction or ThreadedConsoleInteraction()

    def _require_open_chat(
        self, *, need_messages: bool = False, need_metadata: bool = False
    ) -> Optional[dict[str, Any]]:
        """Return current chat or None when required structure is missing."""
        chat_data = self.manager.chat
        if not isinstance(chat_data, dict) or not chat_data:
            return None
        if need_messages and "messages" not in chat_data:
            return None
        if need_metadata and "metadata" not in chat_data:
            return None
        return chat_data

    async def _prompt_text(self, prompt: str) -> str:
        """Prompt user for input through injected interaction adapter."""
        return await self.interaction.prompt_text(prompt)

    async def _confirm_yes(self, prompt: str) -> bool:
        """Return True when user enters 'yes' (case-insensitive)."""
        return (await self._prompt_text(prompt)).strip().lower() == "yes"

    async def _prompt_chat_selection(
        self,
        chats_dir: str,
        *,
        action: str,
        allow_cancel: bool = True,
    ) -> Optional[str]:
        """Prompt user to select a chat through injected interaction adapter."""
        return await self.interaction.prompt_chat_selection(
            chats_dir,
            action=action,
            allow_cancel=allow_cancel,
        )

    async def _update_metadata_and_save(self, **metadata_updates: Any) -> None:
        """Update current chat metadata and persist the chat."""
        chat_data = self._require_open_chat(need_metadata=True)
        if chat_data is None:
            return
        update_metadata(chat_data, **metadata_updates)

    @staticmethod
    def _to_local_time(timestamp: str, format_str: str) -> str:
        """Convert stored UTC-ish timestamp string to local display time."""
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone().strftime(format_str)
        except (ValueError, TypeError, AttributeError):
            return "unknown"

    @staticmethod
    def _message_content_to_text(content: Any) -> str:
        """Normalize message content (list/string) to displayable text."""
        if isinstance(content, list):
            return " ".join(str(part) for part in content)
        return str(content)

    def is_command(self, text: str) -> bool:
        """Check if text is a command.

        Args:
            text: User input text

        Returns:
            True if text starts with /
        """
        return text.strip().startswith("/")

    def parse_command(self, text: str) -> tuple[str, str]:
        """Parse command text into command and arguments.

        Args:
            text: Command text (e.g., "/model gpt-5-mini")

        Returns:
            Tuple of (command, args) where command is without / and args is the rest
        """
        text = text.strip()
        if not text.startswith("/"):
            return "", ""

        parts = text[1:].split(None, 1)
        command = parts[0] if parts else ""
        args = parts[1] if len(parts) > 1 else ""

        return command, args

    def switch_provider_shortcut(self, shortcut: str) -> str:
        """Switch AI provider using shortcut.

        Args:
            shortcut: Provider shortcut (gpt, gem, cla, etc.)

        Returns:
            Confirmation message
        """
        provider = models.resolve_provider_shortcut(shortcut)
        if not provider:
            raise ValueError(f"Unknown provider shortcut: /{shortcut}")

        # Get model for this provider from profile
        model = self.manager.profile["models"].get(provider)
        if not model:
            raise ValueError(f"No model configured for {provider}")

        self.manager.switch_provider(provider, model)

        notices = self._reconcile_provider_modes(provider)
        if notices:
            return f"Switched to {provider} ({model})\n" + "\n".join(notices)
        return f"Switched to {provider} ({model})"

    def _reconcile_provider_modes(self, provider: Optional[str] = None) -> list[str]:
        """Disable incompatible mode flags for the active provider."""
        provider_name = provider or self.manager.current_ai
        notices: list[str] = []

        if self.manager.search_mode and not models.provider_supports_search(provider_name):
            self.manager.search_mode = False
            notices.append(f"Search mode auto-disabled: {provider_name} does not support search.")

        return notices

    def _resolve_chat_path_arg(self, raw_path: str, chats_dir: str) -> str:
        """Resolve chat path argument to an absolute file path.

        Supports:
        - mapped paths (`~/...`, `@/...`, absolute), resolved via path_mapping
        - bare names/relative paths resolved under chats_dir (with traversal protection)
        """
        path = raw_path.strip()
        chats_dir_resolved = Path(chats_dir).resolve()

        # Use shared path mapping for mapped/absolute forms.
        if path.startswith("~/") or path.startswith("@/") or Path(path).is_absolute():
            try:
                mapped = map_path(path)
            except ValueError as e:
                raise ValueError(f"Invalid path: {path}")

            mapped_path = Path(mapped)
            if mapped_path.exists():
                return str(mapped_path)
            raise ValueError(f"Chat not found: {path}")

        # Relative name/path under chats_dir with traversal protection.
        candidate = (Path(chats_dir) / path).resolve()
        try:
            candidate.relative_to(chats_dir_resolved)
        except ValueError:
            raise ValueError(f"Invalid path: {path} (outside chats directory)")

        if not candidate.exists() and not path.endswith(".json"):
            candidate = (Path(chats_dir) / f"{path}.json").resolve()
            try:
                candidate.relative_to(chats_dir_resolved)
            except ValueError:
                raise ValueError(f"Invalid path: {path} (outside chats directory)")

        if candidate.exists():
            return str(candidate)

        raise ValueError(f"Chat not found: {path}")
