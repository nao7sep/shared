"""Metadata, safety, and history command mixin."""

import logging

from .. import hex_id
from ..chat import get_messages_for_ai


class MetadataCommandsMixin:
    async def _invoke_helper_ai(
        self,
        helper_ai: str,
        helper_model: str,
        profile_data: dict,
        messages: list[dict],
        system_prompt: str,
        task: str,
    ) -> str:
        """Late-bind helper call through commands module for test patch compatibility."""
        from .. import commands as commands_module

        return await commands_module.invoke_helper_ai(
            helper_ai,
            helper_model,
            profile_data,
            messages,
            system_prompt,
            task=task,
            session=self.manager,
        )

    async def set_title(self, args: str) -> str:
        """Set chat title.

        Args:
            args: Title text, '--' to clear, or empty to generate with AI

        Returns:
            Confirmation message
        """
        chat_data = self._require_open_chat(need_metadata=True)
        if chat_data is None:
            return "No chat is currently open"

        if not args:
            # Generate title with AI
            return await self.generate_title(args)
        elif args == "--":
            # Clear title
            await self._update_metadata_and_save(title=None)

            return "Title cleared"
        else:
            # Set explicit title
            await self._update_metadata_and_save(title=args)

            return f"Title set to: {args}"

    async def generate_title(self, args: str) -> str:
        """Generate title using AI.

        Args:
            args: Not used

        Returns:
            Generated title or error message
        """
        chat_data = self._require_open_chat(need_messages=True)
        if chat_data is None:
            return "No chat is currently open"

        # Get chat messages for context
        messages = get_messages_for_ai(chat_data)
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
            title = await self._invoke_helper_ai(
                self.manager.helper_ai,
                self.manager.helper_model,
                self.manager.profile,
                prompt_messages,
                system_prompt,
                task="title_generation",
            )

            # Clean up title (remove quotes if present)
            title = title.strip().strip('"').strip("'")

            # Update chat metadata
            await self._update_metadata_and_save(title=title)

            return f"Title generated: {title}"

        except Exception as e:
            logging.error(
                "Helper AI title generation failed (provider=%s, model=%s): %s",
                self.manager.helper_ai,
                self.manager.helper_model,
                e,
                exc_info=True,
            )
            return f"Error generating title: {e}"

    async def set_summary(self, args: str) -> str:
        """Set chat summary.

        Args:
            args: Summary text, '--' to clear, or empty to generate with AI

        Returns:
            Confirmation message
        """
        chat_data = self._require_open_chat(need_metadata=True)
        if chat_data is None:
            return "No chat is currently open"

        if not args:
            # Generate summary with AI
            return await self.generate_summary(args)
        elif args == "--":
            # Clear summary
            await self._update_metadata_and_save(summary=None)

            return "Summary cleared"
        else:
            # Set explicit summary
            await self._update_metadata_and_save(summary=args)

            return "Summary set"

    async def generate_summary(self, args: str) -> str:
        """Generate summary using AI.

        Args:
            args: Not used

        Returns:
            Generated summary or error message
        """
        chat_data = self._require_open_chat(need_messages=True)
        if chat_data is None:
            return "No chat is currently open"

        # Get chat messages for context
        messages = get_messages_for_ai(chat_data)
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
            summary = await self._invoke_helper_ai(
                self.manager.helper_ai,
                self.manager.helper_model,
                self.manager.profile,
                prompt_messages,
                system_prompt,
                task="summary_generation",
            )

            # Update chat metadata
            await self._update_metadata_and_save(summary=summary)

            return f"Summary generated:\n{summary}"

        except Exception as e:
            logging.error(
                "Helper AI summary generation failed (provider=%s, model=%s): %s",
                self.manager.helper_ai,
                self.manager.helper_model,
                e,
                exc_info=True,
            )
            return f"Error generating summary: {e}"

    async def check_safety(self, args: str) -> str:
        """Check chat for unsafe content.

        Args:
            args: Optional hex_id to check specific message, or empty for full chat

        Returns:
            Safety check results with categorized findings
        """
        chat = self.manager.chat
        messages = chat["messages"]

        if not messages:
            return "No messages to check"

        # Determine what to check
        if args.strip():
            # Check specific message by hex ID
            hex_map = self.manager.message_hex_ids
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
            result = await self._invoke_helper_ai(
                self.manager.helper_ai,
                self.manager.helper_model,
                self.manager.profile,
                prompt_messages,
                system_prompt,
                task="safety_check",
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
            logging.error(
                "Helper AI safety check failed (provider=%s, model=%s, scope=%s): %s",
                self.manager.helper_ai,
                self.manager.helper_model,
                scope,
                e,
                exc_info=True,
            )
            return f"Error performing safety check: {e}"

    def _format_message_for_safety_check(self, messages: list[dict]) -> str:
        """Format messages for safety checking.

        Args:
            messages: List of message dictionaries

        Returns:
            Formatted string with message content
        """
        formatted = []

        for msg in messages:
            role = msg.get("role", "unknown")
            content_parts = msg.get("content", [])

            # Get hex ID if available
            hid = msg.get("hex_id")
            hex_label = f"[{hid}] " if isinstance(hid, str) else ""

            content = self._message_content_to_text(content_parts)

            formatted.append(f"{hex_label}{role.upper()}: {content[:500]}")  # Truncate very long messages

        return "\n\n".join(formatted)

    async def show_history(self, args: str) -> str:
        """Show chat history.

        Args:
            args: Optional: number, "all", or "--errors" to filter

        Returns:
            Formatted history display
        """
        chat = self.manager.chat
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
            hex_id = msg.get("hex_id", "???")

            if timestamp:
                time_str = self._to_local_time(timestamp, "%Y-%m-%d %H:%M")
                if time_str == "unknown":
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

            content = self._message_content_to_text(content_parts)

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

        chat = self.manager.chat
        messages = chat["messages"]
        # Look up message by hex ID
        msg_index = hex_id.get_message_index(args.strip(), messages)

        if msg_index is None:
            return f"Invalid hex ID: {args.strip()}"

        msg = messages[msg_index]
        role = msg.get("role", "unknown")
        timestamp = msg.get("timestamp", "unknown")
        content_parts = msg.get("content", [])

        if timestamp and timestamp != "unknown":
            time_str = self._to_local_time(timestamp, "%Y-%m-%d %H:%M:%S")
            if time_str == "unknown":
                time_str = timestamp
        else:
            time_str = "unknown"

        # Role display
        if role == "assistant":
            model = msg.get("model", "unknown")
            role_display = f"Assistant ({model})"
        else:
            role_display = role.capitalize()

        content = self._message_content_to_text(content_parts)

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
        profile_data = self.manager.profile

        profile_path = self.manager.profile_path or "(unknown)"
        chat_path = self.manager.chat_path
        log_file = self.manager.log_file

        chat_data = self.manager.chat or {}
        messages = chat_data.get("messages", []) if isinstance(chat_data, dict) else []
        metadata = chat_data.get("metadata", {}) if isinstance(chat_data, dict) else {}

        timeout = profile_data.get("timeout", 30)
        timeout_display = self.manager.format_timeout(timeout)

        chat_title = metadata.get("title") or "(none)"
        chat_summary = metadata.get("summary") or "(none)"

        updated_local = "(unknown)"
        updated_at = metadata.get("updated_at")
        if updated_at:
            updated_local = self._to_local_time(updated_at, "%Y-%m-%d %H:%M")

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
            f"Assistant:    {self.manager.current_ai} ({self.manager.current_model})",
            f"Helper:       {self.manager.helper_ai} ({self.manager.helper_model})",
            f"System Prompt:{' ' if self.manager.system_prompt_path else ''}{self.manager.system_prompt_path or '(none)'}",
            f"Timeout:      {timeout_display}",
            f"Input Mode:   {self.manager.input_mode}",
            "",
            "Modes",
            f"Secret Mode:  {'ON' if self.manager.secret_mode else 'OFF'}",
            f"Retry Mode:   {'ON' if self.manager.retry_mode else 'OFF'}",
            "",
            "Paths",
            f"Chats Dir:    {profile_data.get('chats_dir', '(unknown)')}",
            f"Log Dir:      {profile_data.get('log_dir', '(unknown)')}",
            "━" * 60,
        ]

        return "\n".join(output)
