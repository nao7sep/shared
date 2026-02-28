"""Metadata generation/safety handlers and compatibility adapters."""

import logging
from typing import TYPE_CHECKING, Optional

from .. import hex_id
from ..domain.chat import ChatMessage
from ..domain.profile import RuntimeProfile
from ..prompts.templates import (
    build_safety_check_prompt,
    build_summary_generation_prompt,
    build_title_generation_prompt,
)
from ..formatting.history import (
    format_for_ai_context,
    format_for_safety_check,
)
from ..formatting.text import make_borderline

if TYPE_CHECKING:
    from .contracts import CommandDependencies as _CommandDependencies
else:
    class _CommandDependencies:
        pass


class MetadataGenerationCommandHandlers:
    """Explicit handlers for metadata generation and safety commands."""

    def __init__(self, dependencies: _CommandDependencies) -> None:
        self._deps = dependencies

    async def _invoke_helper_ai(
        self,
        helper_ai: str,
        helper_model: str,
        profile_data: RuntimeProfile,
        messages: list[ChatMessage],
        system_prompt: Optional[str],
        task: str,
    ) -> str:
        """Invoke helper AI through explicitly wired command context dependency."""
        return await self._deps.context.invoke_helper_ai(
            helper_ai,
            helper_model,
            profile_data,
            messages,
            system_prompt,
            task=task,
            session=self._deps.manager,
        )

    async def set_title(self, args: str) -> str:
        """Set chat title."""
        chat_data = self._deps._require_open_chat(need_metadata=True)
        if chat_data is None:
            return "No chat is currently open"

        if not args:
            return await self.generate_title(args)
        if args == "--":
            await self._deps._update_metadata_and_save(title=None)
            return "Title cleared"

        await self._deps._update_metadata_and_save(title=args)
        return f"Title set to: {args}"

    async def generate_title(self, args: str) -> str:
        """Generate title using helper AI."""
        chat_data = self._deps._require_open_chat(need_messages=True)
        if chat_data is None:
            return "No chat is currently open"

        ai_messages = [m for m in chat_data.messages if m.role in ("user", "assistant")]
        if not ai_messages:
            return "No messages in chat to generate title from"

        context_text = format_for_ai_context(ai_messages)

        prompt_messages = [
            ChatMessage.new_user(
                build_title_generation_prompt(
                    context_text,
                    self._deps.manager.profile.title_prompt,
                )
            )
        ]

        try:
            title = await self._invoke_helper_ai(
                self._deps.manager.helper_ai,
                self._deps.manager.helper_model,
                self._deps.manager.profile,
                prompt_messages,
                None,
                task="title_generation",
            )

            title = title.strip().strip('"').strip("'")
            await self._deps._update_metadata_and_save(title=title)

            return f"Title generated: {title}"

        except Exception as error:
            logging.error(
                "Helper AI title generation failed (provider=%s, model=%s): %s",
                self._deps.manager.helper_ai,
                self._deps.manager.helper_model,
                error,
                exc_info=True,
            )
            return f"Error generating title: {error}"

    async def set_summary(self, args: str) -> str:
        """Set chat summary."""
        chat_data = self._deps._require_open_chat(need_metadata=True)
        if chat_data is None:
            return "No chat is currently open"

        if not args:
            return await self.generate_summary(args)
        if args == "--":
            await self._deps._update_metadata_and_save(summary=None)
            return "Summary cleared"

        await self._deps._update_metadata_and_save(summary=args)
        return "Summary set"

    async def generate_summary(self, args: str) -> str:
        """Generate summary using helper AI."""
        chat_data = self._deps._require_open_chat(need_messages=True)
        if chat_data is None:
            return "No chat is currently open"

        ai_messages = [m for m in chat_data.messages if m.role in ("user", "assistant")]
        if not ai_messages:
            return "No messages in chat to generate summary from"

        context_text = format_for_ai_context(ai_messages)

        prompt_messages = [
            ChatMessage.new_user(
                build_summary_generation_prompt(
                    context_text,
                    self._deps.manager.profile.summary_prompt,
                )
            )
        ]

        try:
            summary = await self._invoke_helper_ai(
                self._deps.manager.helper_ai,
                self._deps.manager.helper_model,
                self._deps.manager.profile,
                prompt_messages,
                None,
                task="summary_generation",
            )

            await self._deps._update_metadata_and_save(summary=summary)
            return f"Summary generated:\n{summary}"

        except Exception as error:
            logging.error(
                "Helper AI summary generation failed (provider=%s, model=%s): %s",
                self._deps.manager.helper_ai,
                self._deps.manager.helper_model,
                error,
                exc_info=True,
            )
            return f"Error generating summary: {error}"

    async def check_safety(self, args: str) -> str:
        """Check chat for unsafe content."""
        chat_data = self._deps._require_open_chat(need_messages=True)
        if chat_data is None:
            return "No chat is currently open"
        messages = chat_data.messages

        if not messages:
            return "No messages to check"

        if args.strip():
            msg_index = hex_id.get_message_index(args.strip(), messages)

            if msg_index is None:
                return f"Invalid hex ID: {args.strip()}"

            content_to_check = format_for_safety_check([messages[msg_index]])
            scope = f"message [{args.strip()}]"
        else:
            content_to_check = format_for_safety_check(messages)
            scope = "entire chat"

        prompt_messages = [
            ChatMessage.new_user(
                build_safety_check_prompt(
                    content_to_check,
                    self._deps.manager.profile.safety_prompt,
                )
            )
        ]

        try:
            result = await self._invoke_helper_ai(
                self._deps.manager.helper_ai,
                self._deps.manager.helper_model,
                self._deps.manager.profile,
                prompt_messages,
                None,
                task="safety_check",
            )

            output = [
                f"Safety Check Results ({scope}):",
                make_borderline(),
                result.strip(),
                make_borderline(),
            ]

            return "\n".join(output)

        except Exception as error:
            logging.error(
                "Helper AI safety check failed (provider=%s, model=%s, scope=%s): %s",
                self._deps.manager.helper_ai,
                self._deps.manager.helper_model,
                scope,
                error,
                exc_info=True,
            )
            return f"Error performing safety check: {error}"


