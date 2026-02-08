"""Command system for PolyChat.

This module handles parsing and executing commands like /model, /gpt, /retry, etc.
"""

import math
from datetime import datetime, timezone
from typing import Optional, Any
from pathlib import Path
from . import models, hex_id, profile
from .helper_ai import invoke_helper_ai
from .chat import (
    update_metadata,
    delete_message_and_following,
    save_chat,
    load_chat,
    get_messages_for_ai,
)
from .chat_manager import (
    prompt_chat_selection,
    generate_chat_filename,
    rename_chat,
    delete_chat as delete_chat_file,
)


class CommandHandler:
    """Handles command parsing and execution."""

    def __init__(self, session_state: dict[str, Any]):
        """Initialize command handler.

        Args:
            session_state: Dictionary containing session state
                - current_ai: Current AI provider
                - current_model: Current model
                - profile: Profile dict
                - chat: Chat dict
        """
        self.session = session_state

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

    async def execute_command(self, text: str) -> Optional[str]:
        """Execute a command.

        Args:
            text: Command text

        Returns:
            Response message, or None if command modifies state silently

        Raises:
            ValueError: If command is invalid
        """
        command, args = self.parse_command(text)

        if not command:
            raise ValueError("Empty command")

        # Provider shortcuts
        if command in ["gpt", "gem", "cla", "grok", "perp", "mist", "deep"]:
            return self.switch_provider_shortcut(command)

        # Other commands
        command_map = {
            "model": self.set_model,
            "helper": self.set_helper,
            "input": self.set_input_mode,
            "timeout": self.set_timeout,
            "system": self.set_system_prompt,
            "retry": self.retry_mode,
            "apply": self.apply_retry,
            "cancel": self.cancel_retry,
            "secret": self.secret_mode_command,
            "rewind": self.rewind_messages,
            "purge": self.purge_messages,
            "history": self.show_history,
            "show": self.show_message,
            "status": self.show_status,
            "title": self.set_title,
            "ai-title": self.generate_title,
            "summary": self.set_summary,
            "ai-summary": self.generate_summary,
            "safe": self.check_safety,
            "new": self.new_chat,
            "open": self.open_chat,
            "switch": self.switch_chat,
            "close": self.close_chat,
            "rename": self.rename_chat_file,
            "delete": self.delete_chat_command,
            "help": self.show_help,
            "exit": self.exit_app,
            "quit": self.exit_app,
        }

        if command in command_map:
            return await command_map[command](args)
        else:
            raise ValueError(f"Unknown command: /{command}")

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
        model = self.session["profile"]["models"].get(provider)
        if not model:
            raise ValueError(f"No model configured for {provider}")

        self.session["current_ai"] = provider
        self.session["current_model"] = model

        return f"Switched to {provider} ({model})"

    def _resolve_chat_path_arg(self, raw_path: str, chats_dir: str) -> str:
        """Resolve chat path argument to an absolute file path.

        Supports:
        - mapped paths (`~/...`, `@/...`, absolute), resolved via profile.map_path
        - bare names/relative paths resolved under chats_dir (with traversal protection)
        """
        path = raw_path.strip()
        chats_dir_resolved = Path(chats_dir).resolve()

        # Use shared path mapping for mapped/absolute forms.
        if path.startswith("~/") or path.startswith("@/") or Path(path).is_absolute():
            try:
                mapped = profile.map_path(path)
            except ValueError as e:
                raise ValueError(f"Invalid path: {path} ({e})")

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

    async def set_model(self, args: str) -> str:
        """Set the current model.

        Args:
            args: Model name, "default" to revert to profile default, or empty to show list

        Returns:
            Confirmation message or model list
        """
        if not args:
            # Show available models for current provider
            provider = self.session["current_ai"]
            available_models = models.get_models_for_provider(provider)
            return f"Available models for {provider}:\n" + "\n".join(
                f"  - {m}" for m in available_models
            )

        # Handle "default" - revert to profile's default
        if args == "default":
            profile = self.session["profile"]
            default_ai = profile["default_ai"]
            default_model = profile["models"][default_ai]

            self.session["current_ai"] = default_ai
            self.session["current_model"] = default_model

            return f"Reverted to profile default: {default_ai} ({default_model})"

        # Check if model exists and switch provider if needed
        provider = models.get_provider_for_model(args)
        if provider:
            self.session["current_ai"] = provider
            self.session["current_model"] = args
            return f"Switched to {provider} ({args})"
        else:
            # Model not in registry, but allow it anyway (might be new)
            self.session["current_model"] = args
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
            helper_ai = self.session.get("helper_ai", "not set")
            helper_model = self.session.get("helper_model", "not set")
            return f"Current helper AI: {helper_ai} ({helper_model})"

        # 'default' - revert to profile default
        if args == "default":
            profile_data = self.session["profile"]
            helper_ai_name = profile_data.get("default_helper_ai", profile_data["default_ai"])
            helper_model_name = profile_data["models"][helper_ai_name]

            self.session["helper_ai"] = helper_ai_name
            self.session["helper_model"] = helper_model_name

            return f"Helper AI restored to profile default: {helper_ai_name} ({helper_model_name})"

        # Otherwise, it's a model name - check if it exists
        provider = models.get_provider_for_model(args)
        if provider:
            self.session["helper_ai"] = provider
            self.session["helper_model"] = args
            return f"Helper AI set to {provider} ({args})"
        else:
            # Model not in registry, but allow it anyway (might be new)
            self.session["helper_model"] = args
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
            timeout = self.session["profile"].get("timeout", 30)
            if timeout == 0:
                return "Current timeout: 0 (wait forever)"
            else:
                return f"Current timeout: {timeout} seconds"

        # Handle "default" - revert to profile's original timeout
        if args == "default":
            # The profile dict is loaded fresh, so we need to reload to get original
            # For now, just use the current profile value or 30
            # Note: This assumes profile hasn't been saved over
            default_timeout = self.session["profile"].get("timeout", 30)
            self.session["profile"]["timeout"] = default_timeout

            # Clear provider cache since timeout changed
            if "_provider_cache" in self.session:
                self.session["_provider_cache"].clear()

            if default_timeout == 0:
                return "Reverted to profile default: 0 (wait forever). Provider cache cleared."
            else:
                return f"Reverted to profile default: {default_timeout} seconds. Provider cache cleared."

        # Parse and set timeout
        try:
            timeout = float(args)
            if not math.isfinite(timeout) or timeout < 0:
                raise ValueError("Timeout must be a non-negative finite number")

            self.session["profile"]["timeout"] = timeout

            # Clear provider cache since timeout changed
            if "_provider_cache" in self.session:
                self.session["_provider_cache"].clear()

            if timeout == 0:
                return "Timeout set to 0 (wait forever). Provider cache cleared."
            else:
                return f"Timeout set to {timeout} seconds. Provider cache cleared."

        except ValueError:
            raise ValueError("Invalid timeout value. Use a number (e.g., /timeout 60) or 0 for no timeout.")

    async def set_input_mode(self, args: str) -> str:
        """Set or show input mode.

        Modes:
            quick: Enter sends, Alt/Option+Enter inserts newline
            compose: Enter inserts newline, Alt/Option+Enter sends
        """
        current_mode = self.session.get("input_mode", "quick")

        if not args:
            if current_mode == "quick":
                return "Input mode: quick (Enter sends, Alt/Option+Enter inserts newline)"
            return "Input mode: compose (Enter inserts newline, Alt/Option+Enter sends)"

        value = args.strip().lower()

        if value == "default":
            profile_mode = self.session["profile"].get("input_mode", "quick")
            if profile_mode not in ("quick", "compose"):
                profile_mode = "quick"
            self.session["input_mode"] = profile_mode
            if profile_mode == "quick":
                return "Input mode restored to profile default: quick"
            return "Input mode restored to profile default: compose"

        if value in ("quick", "compose"):
            self.session["input_mode"] = value
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
        chat = self.session["chat"]

        # Check if chat is loaded
        if not chat or "metadata" not in chat:
            return "No chat is currently open"

        # No args - show current system prompt path
        if not args:
            current_path = chat["metadata"].get("system_prompt_path")
            if current_path:
                return f"Current system prompt: {current_path}"
            else:
                return "No system prompt set for this chat"

        # '--' - remove system prompt
        if args == "--":
            update_metadata(chat, system_prompt_path=None)
            # Also update session state
            self.session["system_prompt"] = None
            self.session["system_prompt_path"] = None

            # Save chat
            chat_path = self.session.get("chat_path")
            if chat_path:
                await save_chat(chat_path, chat)

            return "System prompt removed from chat"

        # 'default' - restore profile default
        if args == "default":
            profile_data = self.session["profile"]
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
            update_metadata(chat, system_prompt_path=system_prompt_path)

            # Update session state
            self.session["system_prompt"] = system_prompt_content
            self.session["system_prompt_path"] = system_prompt_path

            # Save chat
            chat_path = self.session.get("chat_path")
            if chat_path:
                await save_chat(chat_path, chat)

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
            update_metadata(chat, system_prompt_path=args)

            # Update session state
            self.session["system_prompt"] = system_prompt_content
            self.session["system_prompt_path"] = args

            # Save chat
            chat_path = self.session.get("chat_path")
            if chat_path:
                await save_chat(chat_path, chat)

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
        chat = self.session["chat"]

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
        self.session["retry_mode"] = True
        return f"Retry mode enabled. Your next message will replace the last {message_type}."

    async def apply_retry(self, args: str) -> str:
        """Apply current retry attempt and exit retry mode.

        Args:
            args: Not used

        Returns:
            Special signal for REPL loop to handle
        """
        # Check if in retry mode
        if not self.session.get("retry_mode", False):
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
        if not self.session.get("retry_mode", False):
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
        chat = self.session["chat"]

        # Check if chat is loaded
        if not chat or "messages" not in chat:
            return "No chat is currently open"

        # No args - toggle mode
        if not args:
            current_mode = self.session.get("secret_mode", False)
            self.session["secret_mode"] = not current_mode

            if self.session["secret_mode"]:
                return "Secret mode enabled. Messages will not be saved to history."
            else:
                # Signal to clear frozen context
                return "__CLEAR_SECRET_CONTEXT__"

        # Explicit on
        elif args == "on":
            self.session["secret_mode"] = True
            return "Secret mode enabled. Messages will not be saved to history."

        # Explicit off
        elif args == "off":
            self.session["secret_mode"] = False
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
        chat = self.session["chat"]

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
            hex_map = self.session.get("message_hex_ids", {})
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
            hex_map = self.session.get("message_hex_ids", {})
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
                        hex_id_set = self.session.get("hex_id_set", set())
                        hex_id_set.discard(removed_hex)

            # Save chat history after deletion
            chat_path = self.session.get("chat_path")
            if chat_path:
                await save_chat(chat_path, chat)
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

        chat = self.session["chat"]
        messages = chat["messages"]

        if not messages:
            return "No messages to purge"

        # Parse hex IDs
        hex_ids_to_purge = args.strip().split()

        # Validate all hex IDs and get indices
        hex_map = self.session.get("message_hex_ids", {})
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
                hex_id_set = self.session.get("hex_id_set", set())
                hex_id_set.discard(removed_hex)

            deleted_count += 1

        # Rebuild hex_map with updated indices (all messages after deleted ones shift down)
        # Actually, let's just reassign hex IDs since order changed
        # Clear old mappings and regenerate
        hex_map.clear()
        hex_id_set = self.session.get("hex_id_set", set())
        hex_id_set.clear()

        # Reassign hex IDs to remaining messages
        from . import hex_id as hex_id_module
        for i in range(len(messages)):
            new_hex = hex_id_module.generate_hex_id(hex_id_set)
            hex_map[i] = new_hex

        # Save chat history
        chat_path = self.session.get("chat_path")
        if chat_path:
            await save_chat(chat_path, chat)

        # Build warning message
        deleted_ids = ", ".join(f"[{hid}]" for _, hid in sorted(indices_to_delete))
        warning = [
            "⚠️  WARNING: Purging breaks conversation context",
            f"Purged {deleted_count} message(s): {deleted_ids}",
            "Hex IDs have been reassigned to remaining messages."
        ]

        return "\n".join(warning)

    async def set_title(self, args: str) -> str:
        """Set chat title.

        Args:
            args: Title text, '--' to clear, or empty to generate with AI

        Returns:
            Confirmation message
        """
        chat = self.session["chat"]

        # Check if chat is loaded
        if not chat or "metadata" not in chat:
            return "No chat is currently open"

        if not args:
            # Generate title with AI
            return await self.generate_title(args)
        elif args == "--":
            # Clear title
            update_metadata(chat, title=None)

            # Save chat
            chat_path = self.session.get("chat_path")
            if chat_path:
                await save_chat(chat_path, chat)

            return "Title cleared"
        else:
            # Set explicit title
            update_metadata(chat, title=args)

            # Save chat
            chat_path = self.session.get("chat_path")
            if chat_path:
                await save_chat(chat_path, chat)

            return f"Title set to: {args}"

    async def generate_title(self, args: str) -> str:
        """Generate title using AI.

        Args:
            args: Not used

        Returns:
            Generated title or error message
        """
        chat = self.session["chat"]

        # Check if chat is loaded
        if not chat or "messages" not in chat:
            return "No chat is currently open"

        # Get chat messages for context
        messages = get_messages_for_ai(chat)
        if not messages:
            return "No messages in chat to generate title from"

        # Build prompt for title generation
        system_prompt = "You are a helpful assistant that generates concise, descriptive titles for chat conversations. Generate a title that captures the main topic or theme of the conversation in 3-8 words."

        # Take first few messages for context (to keep it efficient)
        context_messages = messages[:10] if len(messages) > 10 else messages
        context_text = "\n".join([
            f"{msg['role']}: {msg.get('content', '')[:200]}"
            for msg in context_messages
        ])

        prompt_messages = [{
            "role": "user",
            "content": f"Generate a short, descriptive title for this conversation:\n\n{context_text}\n\nProvide only the title, nothing else."
        }]

        # Invoke helper AI
        try:
            title = await invoke_helper_ai(
                self.session["helper_ai"],
                self.session["helper_model"],
                self.session["profile"],
                prompt_messages,
                system_prompt
            )

            # Clean up title (remove quotes if present)
            title = title.strip().strip('"').strip("'")

            # Update chat metadata
            update_metadata(chat, title=title)

            # Save chat
            chat_path = self.session.get("chat_path")
            if chat_path:
                await save_chat(chat_path, chat)

            return f"Title generated: {title}"

        except Exception as e:
            return f"Error generating title: {e}"

    async def set_summary(self, args: str) -> str:
        """Set chat summary.

        Args:
            args: Summary text, '--' to clear, or empty to generate with AI

        Returns:
            Confirmation message
        """
        chat = self.session["chat"]

        # Check if chat is loaded
        if not chat or "metadata" not in chat:
            return "No chat is currently open"

        if not args:
            # Generate summary with AI
            return await self.generate_summary(args)
        elif args == "--":
            # Clear summary
            update_metadata(chat, summary=None)

            # Save chat
            chat_path = self.session.get("chat_path")
            if chat_path:
                await save_chat(chat_path, chat)

            return "Summary cleared"
        else:
            # Set explicit summary
            update_metadata(chat, summary=args)

            # Save chat
            chat_path = self.session.get("chat_path")
            if chat_path:
                await save_chat(chat_path, chat)

            return "Summary set"

    async def generate_summary(self, args: str) -> str:
        """Generate summary using AI.

        Args:
            args: Not used

        Returns:
            Generated summary or error message
        """
        chat = self.session["chat"]

        # Check if chat is loaded
        if not chat or "messages" not in chat:
            return "No chat is currently open"

        # Get chat messages for context
        messages = get_messages_for_ai(chat)
        if not messages:
            return "No messages in chat to generate summary from"

        # Build prompt for summary generation
        system_prompt = "You are a helpful assistant that generates concise summaries of chat conversations. Create a brief summary (2-4 sentences) that captures the key topics discussed and main outcomes."

        # Take all messages for full context (summarize everything)
        context_text = "\n".join([
            f"{msg['role']}: {msg.get('content', '')}"
            for msg in messages
        ])

        prompt_messages = [{
            "role": "user",
            "content": f"Generate a concise summary (2-4 sentences) of this conversation:\n\n{context_text}"
        }]

        # Invoke helper AI
        try:
            summary = await invoke_helper_ai(
                self.session["helper_ai"],
                self.session["helper_model"],
                self.session["profile"],
                prompt_messages,
                system_prompt
            )

            # Update chat metadata
            update_metadata(chat, summary=summary)

            # Save chat
            chat_path = self.session.get("chat_path")
            if chat_path:
                await save_chat(chat_path, chat)

            return f"Summary generated:\n{summary}"

        except Exception as e:
            return f"Error generating summary: {e}"

    async def check_safety(self, args: str) -> str:
        """Check chat for unsafe content.

        Args:
            args: Optional hex_id to check specific message, or empty for full chat

        Returns:
            Safety check results with categorized findings
        """
        chat = self.session["chat"]
        messages = chat["messages"]

        if not messages:
            return "No messages to check"

        # Determine what to check
        if args.strip():
            # Check specific message by hex ID
            hex_map = self.session.get("message_hex_ids", {})
            msg_index = hex_id.get_message_index(args.strip(), hex_map)

            if msg_index is None:
                return f"Invalid hex ID: {args.strip()}"

            msg = messages[msg_index]
            content_to_check = self._format_message_for_safety_check([msg])
            scope = f"message [{args.strip()}]"
        else:
            # Check entire chat
            content_to_check = self._format_message_for_safety_check(messages)
            scope = "entire chat"

        # Create safety check prompt for helper AI
        system_prompt = """You are a safety analyzer. Check the provided content for:
1. PII (Personally Identifiable Information) - names, emails, phone numbers, addresses, SSN, etc.
2. Credentials - API keys, passwords, tokens, access keys, secrets
3. Proprietary Information - confidential business data, trade secrets
4. Offensive Content - hate speech, discriminatory language, explicit content

Respond ONLY in this exact format:
PII: [✓ None | ⚠ Found: brief description]
CREDENTIALS: [✓ None | ⚠ Found: brief description]
PROPRIETARY: [✓ None | ⚠ Found: brief description]
OFFENSIVE: [✓ None | ⚠ Found: brief description]

Keep descriptions brief (one line max). For found items, mention location if checking multiple messages."""

        prompt_messages = [{
            "role": "user",
            "content": f"Check this content for safety issues:\n\n{content_to_check}"
        }]

        # Invoke helper AI
        try:
            result = await invoke_helper_ai(
                self.session["helper_ai"],
                self.session["helper_model"],
                self.session["profile"],
                prompt_messages,
                system_prompt
            )

            # Format output
            output = [
                f"Safety Check Results ({scope}):",
                "━" * 40,
                result.strip(),
                "━" * 40,
            ]

            return "\n".join(output)

        except Exception as e:
            return f"Error performing safety check: {e}"

    def _format_message_for_safety_check(self, messages: list[dict]) -> str:
        """Format messages for safety checking.

        Args:
            messages: List of message dictionaries

        Returns:
            Formatted string with message content
        """
        formatted = []
        hex_map = self.session.get("message_hex_ids", {})

        for i, msg in enumerate(messages):
            role = msg.get("role", "unknown")
            content_parts = msg.get("content", [])

            # Get hex ID if available
            hex_label = ""
            if i in hex_map:
                hex_label = f"[{hex_map[i]}] "

            # Format content (join if list, use as-is if string)
            if isinstance(content_parts, list):
                content = " ".join(str(part) for part in content_parts)
            else:
                content = str(content_parts)

            formatted.append(f"{hex_label}{role.upper()}: {content[:500]}")  # Truncate very long messages

        return "\n\n".join(formatted)

    async def show_history(self, args: str) -> str:
        """Show chat history.

        Args:
            args: Optional: number, "all", or "--errors" to filter

        Returns:
            Formatted history display
        """
        chat = self.session["chat"]
        messages = chat["messages"]

        if not messages:
            return "No messages in chat history"

        # Parse arguments
        show_all = False
        errors_only = False
        limit = 10  # Default: last 10 messages

        if args.strip():
            if args.strip() == "all":
                show_all = True
            elif args.strip() == "--errors":
                errors_only = True
            else:
                try:
                    limit = int(args.strip())
                    if limit <= 0:
                        return "Invalid number. Use a positive integer."
                except ValueError:
                    return f"Invalid argument: {args.strip()}. Use a number, 'all', or '--errors'"

        # Filter messages
        if errors_only:
            filtered_messages = [(i, msg) for i, msg in enumerate(messages) if msg.get("role") == "error"]
            display_messages = filtered_messages
            total_count = len(messages)
        elif show_all:
            display_messages = list(enumerate(messages))
            total_count = len(messages)
        else:
            # Show last N messages
            display_messages = list(enumerate(messages))[-limit:]
            total_count = len(messages)

        if not display_messages:
            if errors_only:
                return "No error messages found"
            return "No messages to display"

        # Format output
        hex_map = self.session.get("message_hex_ids", {})
        output = []

        # Header
        if errors_only:
            output.append(f"Error Messages ({len(display_messages)} of {total_count} total messages)")
        elif show_all:
            output.append(f"Chat History (all {total_count} messages)")
        else:
            output.append(f"Chat History (showing {len(display_messages)} of {total_count} messages)")

        output.append("━" * 60)

        # Messages
        for msg_index, msg in display_messages:
            role = msg.get("role", "unknown")
            timestamp = msg.get("timestamp", "")
            content_parts = msg.get("content", [])

            # Get hex ID
            hex_id = hex_map.get(msg_index, "???")

            # Format timestamp (just date and time, no microseconds)
            if timestamp:
                try:
                    # Parse ISO format and simplify
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    time_str = dt.astimezone().strftime("%Y-%m-%d %H:%M")
                except (ValueError, TypeError, AttributeError):
                    time_str = timestamp[:16] if len(timestamp) >= 16 else timestamp
            else:
                time_str = "unknown"

            # Role emoji
            if role == "user":
                role_display = "👤 User"
            elif role == "assistant":
                model = msg.get("model", "unknown")
                role_display = f"🤖 Assistant/{model}"
            elif role == "error":
                role_display = "❌ Error"
            else:
                role_display = f"❓ {role.capitalize()}"

            # Format content (truncate for history view)
            if isinstance(content_parts, list):
                content = " ".join(str(part) for part in content_parts)
            else:
                content = str(content_parts)

            # Truncate long messages
            if len(content) > 100:
                content = content[:97] + "..."

            output.append(f"[{hex_id}] {role_display} ({time_str})")
            output.append(f"  {content}")
            output.append("")

        output.append("━" * 60)

        return "\n".join(output)

    async def show_message(self, args: str) -> str:
        """Show full content of specific message.

        Args:
            args: Hex ID of message to show

        Returns:
            Full message content
        """
        if not args.strip():
            return "Usage: /show <hex_id>"

        chat = self.session["chat"]
        messages = chat["messages"]
        hex_map = self.session.get("message_hex_ids", {})

        # Look up message by hex ID
        msg_index = hex_id.get_message_index(args.strip(), hex_map)

        if msg_index is None:
            return f"Invalid hex ID: {args.strip()}"

        msg = messages[msg_index]
        role = msg.get("role", "unknown")
        timestamp = msg.get("timestamp", "unknown")
        content_parts = msg.get("content", [])

        # Format timestamp
        if timestamp and timestamp != "unknown":
            try:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                time_str = dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError, AttributeError):
                time_str = timestamp
        else:
            time_str = "unknown"

        # Role display
        if role == "assistant":
            model = msg.get("model", "unknown")
            role_display = f"Assistant ({model})"
        else:
            role_display = role.capitalize()

        # Format content
        if isinstance(content_parts, list):
            content = " ".join(str(part) for part in content_parts)
        else:
            content = str(content_parts)

        # Build output
        output = [
            f"Message [{args.strip()}] - {role_display} ({time_str})",
            "━" * 60,
            content,
            "━" * 60,
        ]

        return "\n".join(output)

    async def show_status(self, args: str) -> str:
        """Show current session status and key paths."""
        session = self.session
        profile_data = session["profile"]

        profile_path = session.get("profile_path", "(unknown)")
        profile_name = Path(profile_path).name if profile_path and profile_path != "(unknown)" else "(unknown)"
        chat_path = session.get("chat_path")
        log_file = session.get("log_file")

        chat_data = session.get("chat") or {}
        messages = chat_data.get("messages", []) if isinstance(chat_data, dict) else []
        metadata = chat_data.get("metadata", {}) if isinstance(chat_data, dict) else {}

        timeout = profile_data.get("timeout", 30)
        if timeout == 0:
            timeout_display = "0 (wait forever)"
        else:
            timeout_display = f"{timeout} seconds"

        chat_title = metadata.get("title") or "(none)"
        chat_summary = metadata.get("summary") or "(none)"

        updated_local = "(unknown)"
        updated_at = metadata.get("updated_at")
        if updated_at:
            try:
                dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                updated_local = dt.astimezone().strftime("%Y-%m-%d %H:%M")
            except Exception:
                updated_local = "(unknown)"

        output = [
            "Session Status",
            "━" * 60,
            f"Profile File: {profile_path}",
            f"Chat File:    {chat_path or '(none)'}",
            f"Log File:     {log_file or '(none)'}",
            "",
            "Chat",
            f"Chat Title:   {chat_title}",
            f"Chat Summary: {chat_summary}",
            f"Messages:     {len(messages)}",
            f"Updated:      {updated_local}",
            "",
            "Assistant",
            f"Assistant:    {session.get('current_ai', '(unknown)')} ({session.get('current_model', '(unknown)')})",
            f"Helper:       {session.get('helper_ai', '(unknown)')} ({session.get('helper_model', '(unknown)')})",
            f"System Prompt:{' ' if session.get('system_prompt_path') else ''}{session.get('system_prompt_path') or '(none)'}",
            f"Timeout:      {timeout_display}",
            f"Input Mode:   {session.get('input_mode', 'quick')}",
            "",
            "Modes",
            f"Secret Mode:  {'ON' if session.get('secret_mode') else 'OFF'}",
            f"Retry Mode:   {'ON' if session.get('retry_mode') else 'OFF'}",
            "",
            "Paths",
            f"Chats Dir:    {profile_data.get('chats_dir', '(unknown)')}",
            f"Log Dir:      {profile_data.get('log_dir', '(unknown)')}",
            "━" * 60,
        ]

        return "\n".join(output)

    async def new_chat(self, args: str) -> str:
        """Create new chat file.

        Args:
            args: Optional chat name

        Returns:
            Confirmation message or special __NEW_CHAT__ signal
        """
        chats_dir = self.session["profile"]["chats_dir"]

        # Generate filename
        name = args.strip() if args else None
        new_path = generate_chat_filename(chats_dir, name)

        # Create new chat structure
        new_chat_data = load_chat(new_path)  # Returns empty structure

        # Save empty chat immediately so it appears in /open list
        await save_chat(new_path, new_chat_data)

        # Signal to REPL to switch to new chat
        # Format: __NEW_CHAT__:path
        return f"__NEW_CHAT__:{new_path}"

    async def open_chat(self, args: str) -> str:
        """Open existing chat file.

        Args:
            args: Optional filename or path

        Returns:
            Special __OPEN_CHAT__ signal or error message
        """
        chats_dir = self.session["profile"]["chats_dir"]

        if args.strip():
            # Path provided as argument
            try:
                selected_path = self._resolve_chat_path_arg(args.strip(), chats_dir)
            except ValueError as e:
                return str(e)
        else:
            # Interactive selection
            selected_path = prompt_chat_selection(chats_dir, action="open", allow_cancel=True)

        if not selected_path:
            return "Chat open cancelled"

        # Verify file exists and is valid
        try:
            load_chat(selected_path)
        except Exception as e:
            return f"Error loading chat: {e}"

        # Signal to REPL to switch chat
        # Format: __OPEN_CHAT__:path
        return f"__OPEN_CHAT__:{selected_path}"

    async def switch_chat(self, args: str) -> str:
        """Switch to another chat file.

        Args:
            args: Optional filename or path (shows selection if empty)

        Returns:
            Special __OPEN_CHAT__ signal or error message
        """
        # Reuse /open behavior. The REPL loop saves current chat and opens selected one.
        return await self.open_chat(args)

    async def close_chat(self, args: str) -> str:
        """Close current chat.

        Args:
            args: Not used

        Returns:
            Special __CLOSE_CHAT__ signal
        """
        if not self.session.get("chat_path"):
            return "No chat is currently open"

        # Signal to REPL to close chat
        return "__CLOSE_CHAT__"

    async def rename_chat_file(self, args: str) -> str:
        """Rename a chat file.

        Args:
            args: "<target> <new_name>", where target is "current" or a chat name/path

        Returns:
            Confirmation message or special __RENAME_CURRENT__ signal
        """
        chats_dir = self.session["profile"]["chats_dir"]

        # Parse args
        parts = args.strip().split(None, 1)

        if not parts:
            # No args - prompt for chat to rename
            selected_path = prompt_chat_selection(
                chats_dir, action="rename", allow_cancel=True
            )

            if not selected_path:
                return "Rename cancelled"

            new_name = input("Enter new name: ").strip()
            if not new_name:
                return "Rename cancelled"

            # Perform rename
            try:
                new_path = rename_chat(selected_path, new_name, chats_dir)

                # Check if this was the current chat
                current_path = self.session.get("chat_path")
                if current_path and Path(current_path).resolve() == Path(selected_path).resolve():
                    # Signal to update current chat path
                    return f"__RENAME_CURRENT__:{new_path}"
                else:
                    return f"Renamed: {Path(selected_path).name} → {Path(new_path).name}"

            except Exception as e:
                return f"Error renaming chat: {e}"

        if len(parts) < 2:
            return "Usage: /rename <chat_name|path|current> <new_name>"

        target, new_name = parts[0], parts[1].strip()
        if not new_name:
            return "Usage: /rename <chat_name|path|current> <new_name>"

        if target == "current":
            current_path = self.session.get("chat_path")
            if not current_path:
                return "No chat is currently open"
            old_path = Path(current_path).resolve()
        else:
            try:
                old_path = Path(self._resolve_chat_path_arg(target, chats_dir)).resolve()
            except ValueError as e:
                return str(e)

        try:
            new_path = rename_chat(str(old_path), new_name, chats_dir)

            # Check if this was the current chat
            current_path = self.session.get("chat_path")
            if current_path and Path(current_path).resolve() == old_path.resolve():
                return f"__RENAME_CURRENT__:{new_path}"
            return f"Renamed: {old_path.name} → {Path(new_path).name}"

        except Exception as e:
            return f"Error renaming chat: {e}"

    async def delete_chat_command(self, args: str) -> str:
        """Delete a chat file.

        Args:
            args: Chat name/path, or "current"

        Returns:
            Confirmation message or special __DELETE_CURRENT__ signal
        """
        chats_dir = self.session["profile"]["chats_dir"]

        if not args.strip():
            # Interactive selection
            selected_path = prompt_chat_selection(
                chats_dir, action="delete", allow_cancel=True
            )

            if not selected_path:
                return "Delete cancelled"
        else:
            # Parse argument
            name = args.strip()
            if name == "current":
                current_path = self.session.get("chat_path")
                if not current_path:
                    return "No chat is currently open"
                selected_path = current_path
            else:
                try:
                    selected_path = self._resolve_chat_path_arg(name, chats_dir)
                except ValueError as e:
                    return str(e)

        # Check if this is the current chat
        current_path = self.session.get("chat_path")
        is_current = (
            current_path
            and Path(current_path).resolve() == Path(selected_path).resolve()
        )

        # Perform deletion
        try:
            delete_chat_file(selected_path)

            if is_current:
                # Signal to close current chat
                return f"__DELETE_CURRENT__:{Path(selected_path).name}"
            else:
                return f"Deleted: {Path(selected_path).name}"

        except ValueError as e:
            # Deletion cancelled
            return str(e)
        except Exception as e:
            return f"Error deleting chat: {e}"

    async def show_help(self, args: str) -> str:
        """Show help information.

        Args:
            args: Not used

        Returns:
            Help text
        """
        return """
PolyChat Commands:

Provider Shortcuts:
  /gpt              Switch to OpenAI GPT
  /gem              Switch to Google Gemini
  /cla              Switch to Anthropic Claude
  /grok             Switch to xAI Grok
  /perp             Switch to Perplexity
  /mist             Switch to Mistral
  /deep             Switch to DeepSeek

Model Management:
  /model            Show available models for current provider
  /model <name>     Switch to specified model (auto-detects provider)
  /model default    Restore to profile's default AI and model
  /helper           Show current helper AI model
  /helper <model>   Set helper AI model (for background tasks)
  /helper default   Restore to profile's default helper AI

Configuration:
  /input            Show current input mode
  /input quick      Enter sends, Alt/Option+Enter inserts newline (default)
  /input compose    Enter inserts newline, Alt/Option+Enter sends
  /input default    Restore to profile default input mode
  /timeout          Show current timeout setting
  /timeout <secs>   Set timeout in seconds (0 = wait forever)
  /timeout default  Restore to profile's default timeout
  /system           Show current system prompt path
  /system <path>    Set system prompt (~/ for home, @/ for app root)
  /system --        Remove system prompt from chat
  /system default   Restore to profile's default system prompt

Chat File Management:
  /new [name]       Create new chat file
  /open [name]      Open existing chat file (shows list if no name)
  /switch [name]    Switch chat (save current, then open selected chat)
  /close            Close current chat
  /rename           Select a chat and rename it
  /rename current <new_name>
                    Rename the current chat
  /rename <chat> <new_name>
                    Rename a specific chat by name/path
  /delete current   Delete the current chat (with confirmation)
  /delete [name]    Delete a chat file (shows list if no name)

Chat Control:
  /retry            Enter retry mode (try different responses)
  /apply            Accept current retry attempt and exit retry mode
  /cancel           Abort retry and keep original response
  /secret           Toggle secret mode (messages not saved)
  /secret on/off    Enable/disable secret mode explicitly
  /secret <msg>     Ask one secret question (doesn't toggle mode)
  /rewind <id>      Rewind chat to message (use hex ID or index)
  /rewind last      Rewind to last message
  /purge <hex_id>   Delete specific message(s) (breaks context!)
  /purge <id> <id>  Delete multiple messages

History:
  /history          Show last 10 messages
  /history <n>      Show last n messages
  /history all      Show all messages
  /history --errors Show only error messages
  /show <hex_id>    Show full content of specific message
  /status           Show current profile/chat/session status

Metadata:
  /title            Generate title using AI
  /title <text>     Set chat title
  /title --         Clear title
  /summary          Generate summary using AI
  /summary <text>   Set chat summary
  /summary --       Clear summary

Safety:
  /safe             Check entire chat for unsafe content
  /safe <hex_id>    Check specific message for unsafe content

Other:
  /help             Show this help
  /exit, /quit      Exit PolyChat

Note: Use '--' to delete/clear values (e.g., /title --, /summary --)
"""

    async def exit_app(self, args: str) -> str:
        """Exit the application.

        Args:
            args: Not used

        Returns:
            Exit message (triggers exit in main loop)
        """
        return "__EXIT__"
