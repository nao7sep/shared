"""Runtime and conversation command mixin."""

import math

from .. import hex_id, models, profile
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
            if timeout == 0:
                return "Current timeout: 0 (wait forever)"
            else:
                return f"Current timeout: {timeout} seconds"

        # Handle "default" - revert to profile's original timeout
        if args == "default":
            # The profile dict is loaded fresh, so we need to reload to get original
            # For now, just use the current profile value or 30
            # Note: This assumes profile hasn't been saved over
            default_timeout = self.manager.profile.get("timeout", 30)
            self.manager.profile["timeout"] = default_timeout

            # TODO: Clear provider cache since timeout changed
            # (SessionManager doesn't expose cache clearing yet)

            if default_timeout == 0:
                return "Reverted to profile default: 0 (wait forever)"
            else:
                return f"Reverted to profile default: {default_timeout} seconds"

        # Parse and set timeout
        try:
            timeout = float(args)
            if not math.isfinite(timeout) or timeout < 0:
                raise ValueError("Timeout must be a non-negative finite number")

            self.manager.profile["timeout"] = timeout

            # TODO: Clear provider cache since timeout changed
            # (SessionManager doesn't expose cache clearing yet)

            if timeout == 0:
                return "Timeout set to 0 (wait forever)"
            else:
                return f"Timeout set to {timeout} seconds"

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
            current_path = chat_data["metadata"].get("system_prompt_path")
            if current_path:
                return f"Current system prompt: {current_path}"
            else:
                return "No system prompt set for this chat"

        # '--' - remove system prompt
        if args == "--":
            update_metadata(chat_data, system_prompt_path=None)
            # Also update session state
            self.manager.system_prompt = None
            self.manager.system_prompt_path = None

            await self._save_current_chat_if_open()

            return "System prompt removed from chat"

        # 'default' - restore profile default
        if args == "default":
            profile_data = self.manager.profile
            default_system_prompt = profile_data.get("system_prompt")

            if not default_system_prompt:
                return "No default system prompt configured in profile"

            # Get original unmapped path from profile
            # We need to read the original profile file to get the unmapped path
            # For now, we'll use the profile data's system_prompt if it's a string
            if isinstance(default_system_prompt, str):
                # This is already the mapped path - we need the original
                # For simplicity, we'll just use it as-is (it's already absolute)
                system_prompt_path = default_system_prompt

                # Load the prompt content
                try:
                    system_prompt_mapped_path = profile.map_system_prompt_path(system_prompt_path)
                    with open(system_prompt_mapped_path, "r", encoding="utf-8") as f:
                        system_prompt_content = f.read().strip()
                except Exception as e:
                    raise ValueError(f"Could not load default system prompt: {e}")
            elif isinstance(default_system_prompt, dict):
                # Inline text
                system_prompt_path = None
                system_prompt_content = default_system_prompt.get("content")
            else:
                return "Invalid default system prompt in profile"

            # Update chat metadata
            update_metadata(chat_data, system_prompt_path=system_prompt_path)

            # Update session state
            self.manager.system_prompt = system_prompt_content
            self.manager.system_prompt_path = system_prompt_path

            await self._save_current_chat_if_open()

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
            update_metadata(chat_data, system_prompt_path=args)

            # Update session state
            self.manager.system_prompt = system_prompt_content
            self.manager.system_prompt_path = args

            await self._save_current_chat_if_open()

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
        chat = self.manager.chat

        # Check if chat is loaded
        if not chat or "messages" not in chat:
            return "No chat is currently open"

        messages = chat["messages"]

        # Check if there's an assistant message or error to retry
        if not messages:
            return "No messages to retry"

        last_msg = messages[-1]
        if last_msg["role"] == "assistant":
            message_type = "assistant response"
        elif last_msg["role"] == "error":
            message_type = "error"
        else:
            return "Last message is not an assistant response or error. Nothing to retry."

        # Set retry mode flag - the REPL loop will handle the actual replacement
        self.manager.retry_mode = True
        return f"Retry mode enabled. Your next message will replace the last {message_type}."

    async def apply_retry(self, args: str) -> str:
        """Apply current retry attempt and exit retry mode.

        Args:
            args: Not used

        Returns:
            Special signal for REPL loop to handle
        """
        # Check if in retry mode
        if not self.manager.retry_mode:
            return "Not in retry mode"

        # Signal to REPL loop to apply retry
        return "__APPLY_RETRY__"

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
                return "Secret mode enabled. Messages will not be saved to history."
            else:
                # Signal to clear frozen context
                return "__CLEAR_SECRET_CONTEXT__"

        # Explicit on
        elif args == "on":
            self.manager.secret_mode = True
            return "Secret mode enabled. Messages will not be saved to history."

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
            # Look up hex ID
            hex_map = self.manager.message_hex_ids
            index = hex_id.get_message_index(args, hex_map)
            if index is None:
                raise ValueError(f"Hex ID '{args}' not found")
        else:
            try:
                index = int(args)
            except ValueError:
                raise ValueError("Invalid message index. Use a number, hex ID, or 'last'")

        try:
            # Get hex ID for display (if available)
            hex_map = self.manager.message_hex_ids
            hex_display = hex_id.get_hex_id(index, hex_map)
            hex_str = f" [{hex_display}]" if hex_display else ""

            count = delete_message_and_following(chat, index)

            # Update hex ID tracking - remove deleted messages
            if hex_map:
                # Get the list of indices to remove
                indices_to_remove = list(range(index, index + count))
                for idx in indices_to_remove:
                    if idx in hex_map:
                        removed_hex = hex_map.pop(idx)
                        hex_id_set = self.manager.hex_id_set
                        hex_id_set.discard(removed_hex)

            await self._save_current_chat_if_open()
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
        hex_map = self.manager.message_hex_ids
        indices_to_delete = []

        for hid in hex_ids_to_purge:
            msg_index = hex_id.get_message_index(hid, hex_map)
            if msg_index is None:
                return f"Invalid hex ID: {hid}"
            indices_to_delete.append((msg_index, hid))

        # Sort by index descending so we delete from end to start
        # (avoids index shifting issues)
        indices_to_delete.sort(reverse=True)

        # Delete messages
        deleted_count = 0
        for msg_index, hid in indices_to_delete:
            # Delete the message
            del messages[msg_index]

            # Remove from hex ID tracking
            if msg_index in hex_map:
                removed_hex = hex_map.pop(msg_index)
                hex_id_set = self.manager.hex_id_set
                hex_id_set.discard(removed_hex)

            deleted_count += 1

        # Rebuild hex_map with updated indices (all messages after deleted ones shift down)
        # Actually, let's just reassign hex IDs since order changed
        # Clear old mappings and regenerate
        hex_map.clear()
        hex_id_set = self.manager.hex_id_set
        hex_id_set.clear()

        # Reassign hex IDs to remaining messages
        from .. import hex_id as hex_id_module
        for i in range(len(messages)):
            new_hex = hex_id_module.generate_hex_id(hex_id_set)
            hex_map[i] = new_hex

        await self._save_current_chat_if_open()

        # Build warning message
        deleted_ids = ", ".join(f"[{hid}]" for _, hid in sorted(indices_to_delete))
        warning = [
            "⚠️  WARNING: Purging breaks conversation context",
            f"Purged {deleted_count} message(s): {deleted_ids}",
            "Hex IDs have been reassigned to remaining messages."
        ]

        return "\n".join(warning)
