"""Runtime and conversation command mixin."""

from .. import chat, hex_id, models, profile
from ..chat import delete_message_and_following, update_metadata


class RuntimeCommandsMixin:
    async def set_model(self, args: str) -> str:
        """Set the current model.

        Args:
            args: Model name, "default" to revert to profile default, or empty to show list

        Returns:
            Confirmation message or model list
        """
        if not args:
            # Show available models for current provider
            provider = self.manager.current_ai
            available_models = models.get_models_for_provider(provider)
            return f"Available models for {provider}:\n" + "\n".join(
                f"  - {m}" for m in available_models
            )

        # Handle "default" - revert to profile's default
        if args == "default":
            profile = self.manager.profile
            default_ai = profile["default_ai"]
            default_model = profile["models"][default_ai]

            self.manager.current_ai = default_ai
            self.manager.current_model = default_model

            return f"Reverted to profile default: {default_ai} ({default_model})"

        # Check if model exists and switch provider if needed
        provider = models.get_provider_for_model(args)
        if provider:
            self.manager.current_ai = provider
            self.manager.current_model = args
            return f"Switched to {provider} ({args})"
        else:
            # Model not in registry, but allow it anyway (might be new)
            self.manager.current_model = args
            return f"Set model to {args} (provider: {self.session['current_ai']})"

    async def set_helper(self, args: str) -> str:
        """Set or show the helper AI model.

        Args:
            args: Model name, 'default' to revert, or empty to show current

        Returns:
            Confirmation message or current helper
        """
        if not args:
            # Show current helper
            helper_ai = self.manager.helper_ai
            helper_model = self.manager.helper_model
            return f"Current helper AI: {helper_ai} ({helper_model})"

        # 'default' - revert to profile default
        if args == "default":
            profile_data = self.manager.profile
            helper_ai_name = profile_data.get("default_helper_ai", profile_data["default_ai"])
            helper_model_name = profile_data["models"][helper_ai_name]

            self.manager.helper_ai = helper_ai_name
            self.manager.helper_model = helper_model_name

            return f"Helper AI restored to profile default: {helper_ai_name} ({helper_model_name})"

        # Otherwise, it's a model name - check if it exists
        provider = models.get_provider_for_model(args)
        if provider:
            self.manager.helper_ai = provider
            self.manager.helper_model = args
            return f"Helper AI set to {provider} ({args})"
        else:
            # Model not in registry, but allow it anyway (might be new)
            self.manager.helper_model = args
            return f"Helper model set to {args} (provider: {self.session.get('helper_ai', 'unknown')})"

    async def set_timeout(self, args: str) -> str:
        """Set or show the timeout setting.

        Args:
            args: Timeout in seconds, "default" to revert to profile default, or empty to show current

        Returns:
            Confirmation message or current timeout
        """
        if not args:
            # Show current timeout
            timeout = self.manager.profile.get("timeout", 30)
            return f"Current timeout: {self.manager.format_timeout(timeout)}"

        # Handle "default" - revert to profile's original timeout
        if args == "default":
            default_timeout = self.manager.reset_timeout_to_default()
            return f"Reverted to profile default: {self.manager.format_timeout(default_timeout)}"

        # Parse and set timeout
        try:
            timeout = self.manager.set_timeout(float(args))
            return f"Timeout set to {self.manager.format_timeout(timeout)}"

        except ValueError:
            raise ValueError("Invalid timeout value. Use a number (e.g., /timeout 60) or 0 for no timeout.")

    async def set_input_mode(self, args: str) -> str:
        """Set or show input mode.

        Modes:
            quick: Enter sends, Alt/Option+Enter inserts newline
            compose: Enter inserts newline, Alt/Option+Enter sends
        """
        current_mode = self.manager.input_mode

        if not args:
            if current_mode == "quick":
                return "Input mode: quick (Enter sends, Alt/Option+Enter inserts newline)"
            return "Input mode: compose (Enter inserts newline, Alt/Option+Enter sends)"

        value = args.strip().lower()

        if value == "default":
            profile_mode = self.manager.profile.get("input_mode", "quick")
            if profile_mode not in ("quick", "compose"):
                profile_mode = "quick"
            self.manager.input_mode = profile_mode
            if profile_mode == "quick":
                return "Input mode restored to profile default: quick"
            return "Input mode restored to profile default: compose"

        if value in ("quick", "compose"):
            self.manager.input_mode = value
            if value == "quick":
                return "Input mode set to quick (Enter sends)"
            return "Input mode set to compose (Enter inserts newline)"

        raise ValueError("Invalid input mode. Use /input quick, /input compose, or /input default.")

    async def set_system_prompt(self, args: str) -> str:
        """Set or show system prompt path for current chat session.

        Args:
            args: Path to system prompt file, '--' to remove, 'default' to restore, or empty to show

        Returns:
            Confirmation message
        """
        chat_data = self._require_open_chat(need_metadata=True)
        if chat_data is None:
            return "No chat is currently open"

        # No args - show current system prompt path
        if not args:
            current_path = chat_data["metadata"].get("system_prompt")
            if current_path:
                return f"Current system prompt: {current_path}"
            else:
                return "No system prompt set for this chat"

        # '--' - remove system prompt
        if args == "--":
            update_metadata(chat_data, system_prompt=None)
            # Also update session state
            self.manager.system_prompt = None
            self.manager.system_prompt_path = None

            await self._mark_chat_dirty_if_open()

            return "System prompt removed from chat"

        # 'default' - restore profile default
        if args == "default":
            if not self.manager.profile.get("system_prompt"):
                return "No default system prompt configured in profile"

            (
                system_prompt_content,
                system_prompt_path,
                warning,
            ) = self.manager.load_system_prompt(
                self.manager.profile,
                self.manager.profile_path,
                strict=True,
            )
            if warning:
                raise ValueError(warning)

            # Update chat metadata
            update_metadata(chat_data, system_prompt=system_prompt_path)

            # Update session state
            self.manager.system_prompt = system_prompt_content
            self.manager.system_prompt_path = system_prompt_path

            await self._mark_chat_dirty_if_open()

            return f"System prompt restored to profile default"

        # Otherwise, it's a path - validate and set it
        try:
            # Validate path mapping
            system_prompt_mapped_path = profile.map_system_prompt_path(args)

            # Try to read the file to make sure it exists
            try:
                with open(system_prompt_mapped_path, "r", encoding="utf-8") as f:
                    system_prompt_content = f.read().strip()
            except FileNotFoundError:
                raise ValueError(f"System prompt file not found: {system_prompt_mapped_path}")
            except Exception as e:
                raise ValueError(f"Could not read system prompt file: {e}")

            # Update chat metadata with ORIGINAL path (not mapped)
            update_metadata(chat_data, system_prompt=args)

            # Update session state
            self.manager.system_prompt = system_prompt_content
            self.manager.system_prompt_path = args

            await self._mark_chat_dirty_if_open()

            return f"System prompt set to: {args}"

        except ValueError as e:
            # Re-raise with original error message
            raise

    async def retry_mode(self, args: str) -> str:
        """Enter retry mode (ask again without saving previous attempt).

        Args:
            args: Not used

        Returns:
            Info message
        """
        chat_data = self.manager.chat

        # Check if chat is loaded
        if not chat_data or "messages" not in chat_data:
            return "No chat is currently open"

        messages = chat_data["messages"]

        # Check if there's an assistant message or error to retry
        if not messages:
            return "No messages to retry"

        last_msg = messages[-1]
        if last_msg["role"] not in ("assistant", "error"):
            return "Last message is not an assistant response or error. Nothing to retry."

        # Freeze context and target so /apply <hex_id> can replace the original message.
        ai_messages = chat.get_messages_for_ai(chat_data)
        if last_msg["role"] == "assistant":
            retry_context = ai_messages[:-1]
        else:
            retry_context = ai_messages
        self.manager.enter_retry_mode(
            retry_context,
            target_index=len(messages) - 1,
        )
        return "Retry mode enabled"

    async def apply_retry(self, args: str) -> str:
        """Apply current retry attempt and exit retry mode.

        Args:
            args: Retry candidate hex ID

        Returns:
            Special signal for REPL loop to handle
        """
        # Check if in retry mode
        if not self.manager.retry_mode:
            return "Not in retry mode"

        retry_hex_id = args.strip().lower()
        if not retry_hex_id:
            return "Usage: /apply <hex_id>"
        if not hex_id.is_hex_id(retry_hex_id):
            return f"Invalid hex ID: {args.strip()}"

        # Signal to REPL loop to apply selected retry response
        return f"__APPLY_RETRY__:{retry_hex_id}"

    async def cancel_retry(self, args: str) -> str:
        """Cancel retry mode and keep original messages.

        Args:
            args: Not used

        Returns:
            Special signal for REPL loop to handle
        """
        # Check if in retry mode
        if not self.manager.retry_mode:
            return "Not in retry mode"

        # Signal to REPL loop to cancel retry
        return "__CANCEL_RETRY__"

    async def secret_mode_command(self, args: str) -> str:
        """Toggle or use secret mode (messages not saved to history).

        Args:
            args: Empty to toggle, 'on'/'off' to set explicitly, or message for one-shot

        Returns:
            Status message or special signal for one-shot mode
        """
        chat = self.manager.chat

        # Check if chat is loaded
        if not chat or "messages" not in chat:
            return "No chat is currently open"

        # No args - toggle mode
        if not args:
            current_mode = self.manager.secret_mode
            self.manager.secret_mode = not current_mode

            if self.manager.secret_mode:
                return "Secret mode enabled"
            else:
                # Signal to clear frozen context
                return "__CLEAR_SECRET_CONTEXT__"

        # Explicit on
        elif args == "on":
            self.manager.secret_mode = True
            return "Secret mode enabled"

        # Explicit off
        elif args == "off":
            self.manager.secret_mode = False
            # Signal to clear frozen context
            return "__CLEAR_SECRET_CONTEXT__"

        # Otherwise it's a one-shot secret message
        else:
            # Signal to REPL loop to handle this as one-shot secret message
            return f"__SECRET_ONESHOT__:{args}"

    async def rewind_messages(self, args: str) -> str:
        """Rewind chat history by deleting message at index and all following.

        Args:
            args: Message index (0-based), hex ID, or "last" to rewind to last message

        Returns:
            Confirmation message
        """
        chat = self.manager.chat

        # Check if chat is loaded
        if not chat or "messages" not in chat:
            return "No chat is currently open"

        messages = chat["messages"]

        if not messages:
            return "No messages to delete"

        if args == "last":
            index = len(messages) - 1
        elif hex_id.is_hex_id(args):
            index = hex_id.get_message_index(args, messages)
            if index is None:
                raise ValueError(f"Hex ID '{args}' not found")
        else:
            try:
                index = int(args)
            except ValueError:
                raise ValueError("Invalid message index. Use a number, hex ID, or 'last'")

        try:
            # Get hex ID for display (if available)
            hex_display = hex_id.get_hex_id(index, messages)
            hex_str = f" [{hex_display}]" if hex_display else ""

            count = delete_message_and_following(chat, index)

            await self._mark_chat_dirty_if_open()
            return f"Deleted {count} message(s) from index {index}{hex_str} onwards"
        except IndexError:
            raise ValueError(
                f"Message index {index} out of range (0-{len(messages)-1})"
            )

    async def purge_messages(self, args: str) -> str:
        """Delete specific messages by hex ID (breaks conversation context).

        Args:
            args: Space-separated hex IDs of messages to delete

        Returns:
            Confirmation message with warning
        """
        if not args.strip():
            return "Usage: /purge <hex_id> [hex_id2 hex_id3 ...]"

        chat = self.manager.chat
        messages = chat["messages"]

        if not messages:
            return "No messages to purge"

        # Parse hex IDs
        hex_ids_to_purge = args.strip().split()

        # Validate all hex IDs and get indices
        indices_to_delete = []

        for hid in hex_ids_to_purge:
            msg_index = hex_id.get_message_index(hid, messages)
            if msg_index is None:
                return f"Invalid hex ID: {hid}"
            indices_to_delete.append((msg_index, hid))

        # Sort by index descending so we delete from end to start
        # (avoids index shifting issues)
        indices_to_delete.sort(reverse=True)

        # Delete messages
        deleted_count = 0
        for msg_index, _hid in indices_to_delete:
            # Delete the message
            del messages[msg_index]

            deleted_count += 1

        await self._mark_chat_dirty_if_open()

        # Build warning message
        deleted_ids = ", ".join(f"[{hid}]" for _, hid in sorted(indices_to_delete))
        warning = [
            "⚠️  WARNING: Purging breaks conversation context",
            f"Purged {deleted_count} message(s): {deleted_ids}",
            "Remaining message hex IDs were preserved."
        ]

        return "\n".join(warning)
