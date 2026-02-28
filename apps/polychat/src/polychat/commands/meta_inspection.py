"""Metadata inspection handlers and compatibility adapters."""

from typing import TYPE_CHECKING

from .. import hex_id
from ..formatting.constants import (
    DATETIME_FORMAT_FULL,
    DATETIME_FORMAT_SHORT,
    DISPLAY_NONE,
    DISPLAY_UNKNOWN,
)
from ..formatting.history import (
    create_history_formatter,
    format_for_show,
)
from ..formatting.text import (
    format_messages,
    make_borderline,
    minify_text,
    truncate_text,
)
from ..timeouts import resolve_profile_timeout

if TYPE_CHECKING:
    from .contracts import CommandDependencies as _CommandDependencies
else:
    class _CommandDependencies:
        pass


# Default number of messages shown by /history.
HISTORY_DEFAULT_LIMIT = 10

# One-line preview length for /history and /status.
MESSAGE_PREVIEW_LENGTH = 100


class MetadataInspectionCommandHandlers:
    """Explicit handlers for history/message/status inspection commands."""

    def __init__(self, dependencies: _CommandDependencies) -> None:
        self._deps = dependencies

    async def show_history(self, args: str) -> str:
        """Show chat history."""
        chat_data = self._deps._require_open_chat(need_messages=True)
        if chat_data is None:
            return "No chat is currently open"
        messages = chat_data.messages

        if not messages:
            return "No messages in chat history"

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

        if errors_only:
            filtered_messages = [(i, msg) for i, msg in enumerate(messages) if msg.role == "error"]
            display_messages = filtered_messages
            total_count = len(messages)
        elif show_all:
            display_messages = list(enumerate(messages))
            total_count = len(messages)
        else:
            display_messages = list(enumerate(messages))[-limit:]
            total_count = len(messages)

        if not display_messages:
            if errors_only:
                return "No error messages found"
            return "No messages to display"

        output = []

        if errors_only:
            header = f"Error Messages ({len(display_messages)} of {total_count} total messages)"
        elif show_all:
            header = f"Chat History (all {total_count} messages)"
        else:
            header = f"Chat History (showing {len(display_messages)} of {total_count} messages)"

        output.append(header)

        history_formatter = create_history_formatter(
            self._deps._to_local_time,
            MESSAGE_PREVIEW_LENGTH,
        )

        formatted_messages = format_messages(
            [msg for _, msg in display_messages],
            history_formatter,
        )

        output.append(formatted_messages)

        return "\n".join(output)

    async def show_message(self, args: str) -> str:
        """Show full content of specific message."""
        if not args.strip():
            return "Usage: /show <hex_id>"

        chat_data = self._deps._require_open_chat(need_messages=True)
        if chat_data is None:
            return "No chat is currently open"
        messages = chat_data.messages

        msg_index = hex_id.get_message_index(args.strip(), messages)

        if msg_index is None:
            return f"Invalid hex ID: {args.strip()}"

        msg = messages[msg_index]
        role = msg.role or DISPLAY_UNKNOWN
        timestamp_utc = msg.timestamp_utc or ""

        if timestamp_utc:
            time_str = self._deps._to_local_time(timestamp_utc, DATETIME_FORMAT_FULL)
        else:
            time_str = DISPLAY_UNKNOWN

        if role == "assistant":
            model = msg.model or DISPLAY_UNKNOWN
            role_display = f"Assistant | {model}"
        else:
            role_display = role.capitalize()

        formatted_content = format_for_show([msg])

        output = [
            f"Message [{args.strip()}] | {role_display} | {time_str}",
            formatted_content,
        ]

        return "\n".join(output)

    async def show_status(self, args: str) -> str:
        """Show current session status and key paths."""
        profile_data = self._deps.manager.profile

        profile_path = self._deps.manager.profile_path or DISPLAY_UNKNOWN
        chat_path = self._deps.manager.chat_path
        log_file = self._deps.manager.log_file

        chat_data = self._deps.manager.chat
        messages = chat_data.messages
        metadata = chat_data.metadata

        timeout = resolve_profile_timeout(profile_data)
        timeout_display = self._deps.manager.format_timeout(timeout)

        chat_title = metadata.title or DISPLAY_NONE

        raw_summary = metadata.summary or ""
        if raw_summary:
            chat_summary = truncate_text(minify_text(raw_summary), MESSAGE_PREVIEW_LENGTH)
        else:
            chat_summary = DISPLAY_NONE

        chat_system_prompt = metadata.system_prompt
        if chat_system_prompt:
            try:
                from ..path_utils import map_path

                system_prompt_display = map_path(chat_system_prompt)
            except (ValueError, FileNotFoundError):
                system_prompt_display = chat_system_prompt
        else:
            system_prompt_display = profile_data.system_prompt or DISPLAY_NONE

        title_prompt = profile_data.title_prompt or DISPLAY_NONE
        summary_prompt = profile_data.summary_prompt or DISPLAY_NONE
        safety_prompt = profile_data.safety_prompt or DISPLAY_NONE

        updated_local = DISPLAY_UNKNOWN
        updated_utc = metadata.updated_utc
        if updated_utc:
            updated_local = self._deps._to_local_time(updated_utc, DATETIME_FORMAT_SHORT)

        output = [
            "Session Status",
            make_borderline(),
            "Directories",
            f"Chats:     {profile_data.chats_dir}",
            f"Logs:      {profile_data.logs_dir}",
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
            f"Assistant: {self._deps.manager.current_ai} | {self._deps.manager.current_model}",
            f"Helper:    {self._deps.manager.helper_ai} | {self._deps.manager.helper_model}",
            "",
            "Prompts",
            f"System:    {system_prompt_display}",
            f"Title:     {title_prompt}",
            f"Summary:   {summary_prompt}",
            f"Safety:    {safety_prompt}",
            "",
            "Modes",
            f"Input:     {self._deps.manager.input_mode}",
            f"Retry:     {'ON' if self._deps.manager.retry_mode else 'OFF'}",
            f"Secret:    {'ON' if self._deps.manager.secret_mode else 'OFF'}",
            f"Search:    {'ON' if self._deps.manager.search_mode else 'OFF'}",
            f"Timeout:   {timeout_display}",
            make_borderline(),
        ]

        return "\n".join(output)


