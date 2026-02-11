"""Runtime and conversation command mixin."""

from .. import chat, hex_id, models, profile
from ..chat import delete_message_and_following, update_metadata
from ..timeouts import resolve_profile_timeout
from .types import CommandResult, CommandSignal


class RuntimeCommandsMixin:
    async def _choose_model_from_candidates(
        self,
        query: str,
        candidates: list[str],
    ) -> tuple[str | None, str | None]:
        """Prompt user to select one model when multiple candidates match."""
        prompt_lines = [f"Multiple models match '{query}':"]
        for index, model_name in enumerate(candidates, start=1):
            provider_name = models.get_provider_for_model(model_name) or "unknown"
            prompt_lines.append(f"  {index}. {model_name} ({provider_name})")
        prompt_lines.append("Select one by number (press Enter to cancel).")

        answer = (await self._prompt_text("\n".join(prompt_lines) + "\nSelection: ")).strip()
        if not answer:
            return None, "Model selection cancelled."
        if not answer.isdigit():
            return None, "Invalid selection. Enter a number from the list."

        selected_index = int(answer)
        if selected_index < 1 or selected_index > len(candidates):
            return None, f"Invalid selection. Choose a number between 1 and {len(candidates)}."

        return candidates[selected_index - 1], None

    async def _resolve_model_selection(self, query: str) -> tuple[str | None, str]:
        """Resolve a model query to one selected model."""
        candidates = models.resolve_model_candidates(query)
        if not candidates:
            return None, f"No model matches '{query}'."
        if len(candidates) == 1:
            return candidates[0], ""

        selected_model, selection_error = await self._choose_model_from_candidates(
            query, candidates
        )
        if selection_error:
            return None, selection_error
        if selected_model is None:
            return None, "Model selection cancelled."
        return selected_model, ""

    async def set_model(self, args: str) -> str:
        """Set the current model.

        Args:
            args: Model query, "default" to revert to profile default, or empty to show list

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
            profile_data = self.manager.profile
            default_ai = profile_data["default_ai"]
            default_model = profile_data["models"][default_ai]

            self.manager.current_ai = default_ai
            self.manager.current_model = default_model

            notices = self._reconcile_provider_modes(default_ai)
            if notices:
                return f"Reverted to profile default: {default_ai} ({default_model})\n" + "\n".join(notices)
            return f"Reverted to profile default: {default_ai} ({default_model})"

        query = args.strip()
        selected_model, resolution_error = await self._resolve_model_selection(query)
        if resolution_error:
            return resolution_error
        if selected_model is None:
            return "Model selection cancelled."

        provider = models.get_provider_for_model(selected_model)
        if provider is None:
            return f"No provider found for model '{selected_model}'."

        self.manager.current_ai = provider
        self.manager.current_model = selected_model

        base_message = f"Switched to {provider} ({selected_model})"
        if selected_model != query:
            base_message += f" [matched from '{query}']"
        notices = self._reconcile_provider_modes(provider)
        if notices:
            return base_message + "\n" + "\n".join(notices)
        return base_message

    async def set_helper(self, args: str) -> str:
        """Set or show the helper AI model.

        Args:
            args: Model query/provider shortcut, 'default' to revert, or empty to show current

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

        query = args.strip()
        lowered = query.lower()

        # Allow provider shortcuts (/helper gpt, /helper gem, etc.).
        provider_shortcut = models.resolve_provider_shortcut(lowered)
        if provider_shortcut is not None:
            provider_model = self.manager.profile["models"].get(provider_shortcut)
            if not provider_model:
                return f"No model configured for {provider_shortcut} in profile"
            self.manager.helper_ai = provider_shortcut
            self.manager.helper_model = provider_model
            return f"Helper AI set to {provider_shortcut} ({provider_model})"

        if lowered in models.get_all_providers():
            provider_model = self.manager.profile["models"].get(lowered)
            if not provider_model:
                return f"No model configured for {lowered} in profile"
            self.manager.helper_ai = lowered
            self.manager.helper_model = provider_model
            return f"Helper AI set to {lowered} ({provider_model})"

        selected_model, resolution_error = await self._resolve_model_selection(query)
        if resolution_error:
            return resolution_error
        if selected_model is None:
            return "Helper model selection cancelled."

        provider = models.get_provider_for_model(selected_model)
        if provider is None:
            return f"No provider found for model '{selected_model}'."

        self.manager.helper_ai = provider
        self.manager.helper_model = selected_model

        message = f"Helper AI set to {provider} ({selected_model})"
        if selected_model != query:
            message += f" [matched from '{query}']"
        return message

    async def set_timeout(self, args: str) -> str:
        """Set or show the timeout setting.

        Args:
            args: Timeout in seconds, "default" to revert to profile default, or empty to show current

        Returns:
            Confirmation message or current timeout
        """
        if not args:
            # Show current timeout
            timeout = resolve_profile_timeout(self.manager.profile)
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

        # No args - show current system prompt path (prefer chat metadata/raw path)
        if not args:
            current_path = chat_data["metadata"].get("system_prompt") or self.manager.system_prompt_path
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

            return "System prompt restored to profile default"

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
            except Exception:
                raise ValueError(f"Could not read system prompt file: {system_prompt_mapped_path}")

            # Update chat metadata with ORIGINAL path (not mapped)
            update_metadata(chat_data, system_prompt=args)

            # Update session state
            self.manager.system_prompt = system_prompt_content
            self.manager.system_prompt_path = args

            await self._mark_chat_dirty_if_open()

            return f"System prompt set to: {args}"

        except ValueError:
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
        retry_context = chat.get_retry_context_for_last_interaction(chat_data)
        self.manager.enter_retry_mode(
            retry_context,
            target_index=len(messages) - 1,
        )
        return "Retry mode enabled"

    async def apply_retry(self, args: str) -> CommandResult:
        """Apply current retry attempt and exit retry mode.

        Args:
            args: Retry candidate hex ID, or empty/'last' for most recent attempt

        Returns:
            Special signal for REPL loop to handle
        """
        # Check if in retry mode
        if not self.manager.retry_mode:
            return "Not in retry mode"

        normalized_args = args.strip().lower()
        if normalized_args in {"", "last"}:
            retry_hex_id = self.manager.get_latest_retry_attempt_id()
            if not retry_hex_id:
                return "No retry attempts available yet"
            return CommandSignal(kind="apply_retry", value=retry_hex_id)

        retry_hex_id = normalized_args
        if not hex_id.is_hex_id(retry_hex_id):
            return f"Invalid hex ID: {args.strip()}"

        # Signal to REPL loop to apply selected retry response
        return CommandSignal(kind="apply_retry", value=retry_hex_id)

    async def cancel_retry(self, args: str) -> CommandResult:
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
        return CommandSignal(kind="cancel_retry")

    async def secret_mode_command(self, args: str) -> str:
        """Show or set secret mode (messages not saved to history).

        Args:
            args: Empty to show status or 'on'/'off' to set explicitly

        Returns:
            Status message
        """
        chat_data = self.manager.chat

        # Check if chat is loaded
        if not chat_data or "messages" not in chat_data:
            return "No chat is currently open"

        normalized = args.strip().lower()

        # No args - show current mode
        if not normalized:
            return "Secret mode: on" if self.manager.secret_mode else "Secret mode: off"

        # Explicit on
        if normalized == "on":
            if self.manager.secret_mode:
                return "Secret mode already on"
            secret_context = chat.get_messages_for_ai(chat_data)
            # Store a snapshot for state/diagnostics; secret turns are not persisted.
            self.manager.enter_secret_mode(secret_context)
            return "Secret mode enabled"

        # Explicit off
        if normalized == "off":
            if self.manager.secret_mode:
                self.manager.exit_secret_mode()
                return "Secret mode disabled"
            return "Secret mode already off"

        # Common typo from help-style notation should not be treated as message.
        if normalized in {"on/off", "on|off"}:
            return "Use /secret on or /secret off"

        raise ValueError("Invalid argument. Use /secret on or /secret off")

    async def search_mode_command(self, args: str) -> str:
        """Show or set search mode (web search enabled).

        Args:
            args: Empty to show status or 'on'/'off' to toggle

        Returns:
            Status message
        """
        from ..models import provider_supports_search, SEARCH_SUPPORTED_PROVIDERS

        chat_data = self.manager.chat

        if not chat_data or "messages" not in chat_data:
            return "No chat is currently open"

        normalized = args.strip().lower()

        # No args - show current mode + supported providers
        if not normalized:
            status = "on" if self.manager.search_mode else "off"
            providers = ", ".join(sorted(SEARCH_SUPPORTED_PROVIDERS))
            return f"Search mode: {status}\nSupported providers: {providers}"

        # Explicit on
        if normalized == "on":
            if not provider_supports_search(self.manager.current_ai):
                providers = ", ".join(sorted(SEARCH_SUPPORTED_PROVIDERS))
                return f"Search not supported for {self.manager.current_ai}. Supported: {providers}"
            if self.manager.search_mode:
                return "Search mode already on"
            self.manager.search_mode = True
            return "Search mode enabled"

        # Explicit off
        if normalized == "off":
            if self.manager.search_mode:
                self.manager.search_mode = False
                return "Search mode disabled"
            return "Search mode already off"

        # Typo hint
        if normalized in {"on/off", "on|off"}:
            return "Use /search on or /search off"

        raise ValueError("Invalid argument. Use /search on or /search off")

    async def rewind_messages(self, args: str) -> str:
        """Rewind chat history by deleting a target message and all following.

        Args:
            args: Message hex ID, or empty/"last" (last user+assistant/user+error pair, or trailing error)

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

        target = args.strip().lower()
        if not target:
            target = "last"

        if target == "last":
            tail = messages[-1]
            tail_role = tail.get("role")

            if tail_role == "error":
                # If error follows a user message, treat it as one failed interaction.
                if len(messages) >= 2 and messages[-2].get("role") == "user":
                    index = len(messages) - 2
                else:
                    # Standalone trailing error (e.g., after a completed turn).
                    index = len(messages) - 1
            else:
                if len(messages) < 2:
                    raise ValueError("No complete turn to delete")
                prev = messages[-2]
                if tail_role != "assistant" or prev.get("role") != "user":
                    raise ValueError(
                        "Last interaction is not a complete user+assistant or user+error turn"
                    )
                index = len(messages) - 2
        elif hex_id.is_hex_id(target):
            index = hex_id.get_message_index(target, messages)
            if index is None:
                raise ValueError(f"Hex ID '{target}' not found")
        else:
            raise ValueError("Invalid target. Use a hex ID or 'last'")

        try:
            # Get hex ID for display (if available)
            hex_display = hex_id.get_hex_id(index, messages)
            if hex_display:
                target_label = f"[{hex_display}]"
            elif target == "last":
                target_label = "last error" if messages[index].get("role") == "error" else "last turn"
            else:
                target_label = "selected target"

            print(f"WARNING: Rewind will delete from {target_label} onwards")
            if not await self._confirm_yes("Type 'yes' to confirm rewind: "):
                return "Rewind cancelled"

            # Clean up hex IDs for all messages that will be deleted
            messages = chat["messages"]
            for i in range(len(messages) - 1, index - 1, -1):
                self.manager.remove_message_hex_id(i)

            count = delete_message_and_following(chat, index)

            await self._mark_chat_dirty_if_open()
            if hex_display:
                return f"Deleted {count} message(s) from [{hex_display}] onwards"
            return f"Deleted {count} message(s)"
        except IndexError:
            raise ValueError("Message target is out of range")

    async def purge_messages(self, args: str) -> str:
        """Delete specific messages by hex ID (breaks conversation context).

        Args:
            args: Space-separated hex IDs of messages to delete

        Returns:
            Confirmation message
        """
        if not args.strip():
            return "Usage: /purge <hex_id> [hex_id2 hex_id3 ...]"

        chat = self._require_open_chat(need_messages=True)
        if chat is None:
            return "No chat is currently open"

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

        # Confirm destructive operation
        ids_for_prompt = ", ".join(f"[{hid}]" for _, hid in sorted(indices_to_delete))
        print(f"WARNING: Purging message(s) breaks conversation context: {ids_for_prompt}")
        if not await self._confirm_yes("Type 'yes' to confirm purge: "):
            return "Purge cancelled"

        # Delete messages
        deleted_count = 0
        for msg_index, _hid in indices_to_delete:
            # Clean up hex ID before deleting
            self.manager.remove_message_hex_id(msg_index)
            del messages[msg_index]

            deleted_count += 1

        await self._mark_chat_dirty_if_open()

        # Build confirmation message
        deleted_ids = ", ".join(f"[{hid}]" for _, hid in sorted(indices_to_delete))
        return f"Purged {deleted_count} message(s): {deleted_ids}"
