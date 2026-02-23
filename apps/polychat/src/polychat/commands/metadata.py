"""Metadata, safety, and history command mixin."""

import logging
from typing import TYPE_CHECKING, Optional

from .. import hex_id
from ..chat import get_messages_for_ai
from ..constants import (
    DATETIME_FORMAT_FULL,
    DATETIME_FORMAT_SHORT,
    DISPLAY_NONE,
    DISPLAY_UNKNOWN,
    HISTORY_DEFAULT_LIMIT,
    MESSAGE_PREVIEW_LENGTH,
)
from ..text_formatting import (
    format_for_ai_context,
    format_for_safety_check,
    format_for_show,
    format_messages,
    create_history_formatter,
    make_borderline,
    minify_text,
    truncate_text,
)
from ..prompts import (
    build_safety_check_prompt,
    build_summary_generation_prompt,
    build_title_generation_prompt,
)
from ..timeouts import resolve_profile_timeout

if TYPE_CHECKING:
    from .contracts import CommandDependencies as _CommandDependencies
else:
    class _CommandDependencies:
        pass


class MetadataCommandsMixin(_CommandDependencies):
    async def _invoke_helper_ai(
        self,
        helper_ai: str,
        helper_model: str,
        profile_data: dict,
        messages: list[dict],
        system_prompt: Optional[str],
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

        context_text = format_for_ai_context(messages)

        prompt_messages = [{
            "role": "user",
            "content": build_title_generation_prompt(
                context_text,
                self.manager.profile.get("title_prompt")
            ),
        }]

        # Invoke helper AI
        try:
            title = await self._invoke_helper_ai(
                self.manager.helper_ai,
                self.manager.helper_model,
                self.manager.profile,
                prompt_messages,
                None,
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

        # Take all messages for full context (summarize everything)
        context_text = format_for_ai_context(messages)

        prompt_messages = [{
            "role": "user",
            "content": build_summary_generation_prompt(
                context_text,
                self.manager.profile.get("summary_prompt")
            ),
        }]

        # Invoke helper AI
        try:
            summary = await self._invoke_helper_ai(
                self.manager.helper_ai,
                self.manager.helper_model,
                self.manager.profile,
                prompt_messages,
                None,
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
        chat_data = self._require_open_chat(need_messages=True)
        if chat_data is None:
            return "No chat is currently open"
        messages = chat_data["messages"]

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
            content_to_check = format_for_safety_check([msg])
            scope = f"message [{args.strip()}]"
        else:
            # Check entire chat
            content_to_check = format_for_safety_check(messages)
            scope = "entire chat"

        # Create safety check prompt for helper AI
        prompt_messages = [{
            "role": "user",
            "content": build_safety_check_prompt(
                content_to_check,
                self.manager.profile.get("safety_prompt")
            ),
        }]

        # Invoke helper AI
        try:
            result = await self._invoke_helper_ai(
                self.manager.helper_ai,
                self.manager.helper_model,
                self.manager.profile,
                prompt_messages,
                None,
                task="safety_check",
            )

            # Format output
            output = [
                f"Safety Check Results ({scope}):",
                make_borderline(),
                result.strip(),
                make_borderline(),
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

    async def show_history(self, args: str) -> str:
        """Show chat history.

        Args:
            args: Optional: number, "all", or "errors" to filter

        Returns:
            Formatted history display
        """
        chat_data = self._require_open_chat(need_messages=True)
        if chat_data is None:
            return "No chat is currently open"
        messages = chat_data["messages"]

        if not messages:
            return "No messages in chat history"

        # Parse arguments
        show_all = False
        errors_only = False
        limit = HISTORY_DEFAULT_LIMIT

        if args.strip():
            if args.strip() == "all":
                show_all = True
            elif args.strip() == "errors":
                errors_only = True
            else:
                try:
                    limit = int(args.strip())
                    if limit <= 0:
                        return "Invalid number. Use a positive integer."
                except ValueError:
                    return f"Invalid argument: {args.strip()}. Use a number, 'all', or 'errors'"

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
            header = f"Error Messages ({len(display_messages)} of {total_count} total messages)"
        elif show_all:
            header = f"Chat History (all {total_count} messages)"
        else:
            header = f"Chat History (showing {len(display_messages)} of {total_count} messages)"

        output.append(header)

        # Format messages using history formatter
        history_formatter = create_history_formatter(
            self._to_local_time,
            MESSAGE_PREVIEW_LENGTH
        )

        formatted_messages = format_messages(
            [msg for _, msg in display_messages],
            history_formatter,
        )

        output.append(formatted_messages)

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

        chat_data = self._require_open_chat(need_messages=True)
        if chat_data is None:
            return "No chat is currently open"
        messages = chat_data["messages"]
        # Look up message by hex ID
        msg_index = hex_id.get_message_index(args.strip(), messages)

        if msg_index is None:
            return f"Invalid hex ID: {args.strip()}"

        msg = messages[msg_index]
        role = msg.get("role", DISPLAY_UNKNOWN)
        timestamp = msg.get("timestamp", "")

        if timestamp:
            time_str = self._to_local_time(timestamp, DATETIME_FORMAT_FULL)
            # If formatter returns DISPLAY_UNKNOWN, keep it as is
        else:
            time_str = DISPLAY_UNKNOWN

        # Role display
        if role == "assistant":
            model = msg.get("model", DISPLAY_UNKNOWN)
            role_display = f"Assistant | {model}"
        else:
            role_display = role.capitalize()

        # Format content with borderlines
        formatted_content = format_for_show([msg])

        # Build output
        output = [
            f"Message [{args.strip()}] | {role_display} | {time_str}",
            formatted_content,
        ]

        return "\n".join(output)

    async def show_status(self, args: str) -> str:
        """Show current session status and key paths."""
        profile_data = self.manager.profile

        profile_path = self.manager.profile_path or DISPLAY_UNKNOWN
        chat_path = self.manager.chat_path
        log_file = self.manager.log_file

        chat_data = self.manager.chat or {}
        messages = chat_data.get("messages", []) if isinstance(chat_data, dict) else []
        metadata = chat_data.get("metadata", {}) if isinstance(chat_data, dict) else {}

        timeout = resolve_profile_timeout(profile_data)
        timeout_display = self.manager.format_timeout(timeout)

        chat_title = metadata.get("title") or DISPLAY_NONE
        
        # Truncate summary for display (minify + truncate like history messages)
        raw_summary = metadata.get("summary") or ""
        if raw_summary:
            chat_summary = truncate_text(minify_text(raw_summary), MESSAGE_PREVIEW_LENGTH)
        else:
            chat_summary = DISPLAY_NONE
        
        # Get system prompt path for display (needs mapping if from chat metadata)
        chat_system_prompt = metadata.get("system_prompt")
        if chat_system_prompt:
            # Chat has override - map it to absolute path for display
            try:
                from ..path_utils import map_path
                system_prompt_display = map_path(chat_system_prompt)
            except (ValueError, FileNotFoundError):
                system_prompt_display = chat_system_prompt  # Fall back if mapping fails
        else:
            # Use profile default (already mapped in profile_data)
            system_prompt_display = profile_data.get("system_prompt", DISPLAY_NONE)

        # Get helper prompt paths from profile (already mapped)
        title_prompt = profile_data.get("title_prompt", DISPLAY_NONE)
        summary_prompt = profile_data.get("summary_prompt", DISPLAY_NONE)
        safety_prompt = profile_data.get("safety_prompt", DISPLAY_NONE)

        updated_local = DISPLAY_UNKNOWN
        updated_at = metadata.get("updated_at")
        if updated_at:
            updated_local = self._to_local_time(updated_at, DATETIME_FORMAT_SHORT)

        output = [
            "Session Status",
            make_borderline(),
            "Directories",
            f"Chats:     {profile_data.get('chats_dir', DISPLAY_UNKNOWN)}",
            f"Logs:      {profile_data.get('logs_dir', DISPLAY_UNKNOWN)}",
            "",
            "Files",
            f"Profile:   {profile_path}",
            f"Chat:      {chat_path or DISPLAY_NONE}",
            f"Log:       {log_file or DISPLAY_NONE}",
            "",
            "Chat",
            f"Title:     {chat_title}",
            f"Summary:   {chat_summary}",
            f"Messages:  {len(messages)}",
            f"Updated:   {updated_local}",
            "",
            "Providers",
            f"Assistant: {self.manager.current_ai} | {self.manager.current_model}",
            f"Helper:    {self.manager.helper_ai} | {self.manager.helper_model}",
            "",
            "Prompts",
            f"System:    {system_prompt_display}",
            f"Title:     {title_prompt}",
            f"Summary:   {summary_prompt}",
            f"Safety:    {safety_prompt}",
            "",
            "Modes",
            f"Input:     {self.manager.input_mode}",
            f"Retry:     {'ON' if self.manager.retry_mode else 'OFF'}",
            f"Secret:    {'ON' if self.manager.secret_mode else 'OFF'}",
            f"Search:    {'ON' if self.manager.search_mode else 'OFF'}",
            f"Timeout:   {timeout_display}",
            make_borderline(),
        ]

        return "\n".join(output)
