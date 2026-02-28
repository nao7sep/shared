"""Runtime mutation handlers and compatibility adapters."""

from typing import TYPE_CHECKING

from .. import hex_id
from ..chat import delete_message_and_following

if TYPE_CHECKING:
    from .contracts import CommandDependencies as _CommandDependencies
else:
    class _CommandDependencies:
        pass


class RuntimeMutationCommandHandlers:
    """Explicit handlers for destructive history-mutation commands."""

    def __init__(self, dependencies: _CommandDependencies) -> None:
        self._deps = dependencies

    async def rewind_messages(self, args: str) -> str:
        """Rewind chat history by deleting a target message and all following."""
        chat_data = self._deps.manager.chat

        if not chat_data.messages and not self._deps.manager.chat_path:
            return "No chat is currently open"

        messages = chat_data.messages

        if not messages:
            return "No messages to delete"

        target = args.strip().lower()
        if not target:
            target = "last"

        if target == "last":
            tail = messages[-1]
            tail_role = tail.role

            if tail_role == "error":
                if len(messages) >= 2 and messages[-2].role == "user":
                    index = len(messages) - 2
                else:
                    index = len(messages) - 1
            else:
                if len(messages) < 2:
                    raise ValueError("No complete turn to delete")
                prev = messages[-2]
                if tail_role != "assistant" or prev.role != "user":
                    raise ValueError(
                        "Last interaction is not a complete user+assistant or user+error turn"
                    )
                index = len(messages) - 2
        elif hex_id.is_hex_id(target):
            found_index = hex_id.get_message_index(target, messages)
            if found_index is None:
                raise ValueError(f"Hex ID '{target}' not found")
            index = found_index
        else:
            raise ValueError("Invalid target. Use a hex ID or 'last'")

        try:
            hex_display = hex_id.get_hex_id(index, messages)
            if hex_display:
                target_label = f"[{hex_display}]"
            elif target == "last":
                target_label = "last error" if messages[index].role == "error" else "last turn"
            else:
                target_label = "selected target"

            await self._deps._notify(f"WARNING: Rewind will delete from {target_label} onwards")
            if not await self._deps._confirm_yes("Type 'yes' to confirm rewind: "):
                return "Rewind cancelled"

            messages = chat_data.messages
            for index_to_remove in range(len(messages) - 1, index - 1, -1):
                self._deps.manager.remove_message_hex_id(index_to_remove)

            count = delete_message_and_following(chat_data, index)

            if hex_display:
                return f"Deleted {count} message(s) from [{hex_display}] onwards"
            return f"Deleted {count} message(s)"
        except IndexError:
            raise ValueError("Message target is out of range")

    async def purge_messages(self, args: str) -> str:
        """Delete specific messages by hex ID (breaks conversation context)."""
        if not args.strip():
            return "Usage: /purge <hex_id> [hex_id2 hex_id3 ...]"

        chat_data = self._deps._require_open_chat(need_messages=True)
        if chat_data is None:
            return "No chat is currently open"

        messages = chat_data.messages

        if not messages:
            return "No messages to purge"

        hex_ids_to_purge = args.strip().split()
        indices_to_delete = []

        for hid in hex_ids_to_purge:
            msg_index = hex_id.get_message_index(hid, messages)
            if msg_index is None:
                return f"Invalid hex ID: {hid}"
            indices_to_delete.append((msg_index, hid))

        indices_to_delete.sort(reverse=True)

        ids_for_prompt = ", ".join(f"[{hid}]" for _, hid in sorted(indices_to_delete))
        await self._deps._notify(
            f"WARNING: Purging message(s) breaks conversation context: {ids_for_prompt}"
        )
        if not await self._deps._confirm_yes("Type 'yes' to confirm purge: "):
            return "Purge cancelled"

        deleted_count = 0
        for msg_index, _hid in indices_to_delete:
            self._deps.manager.remove_message_hex_id(msg_index)
            del messages[msg_index]
            deleted_count += 1

        deleted_ids = ", ".join(f"[{hid}]" for _, hid in sorted(indices_to_delete))
        return f"Purged {deleted_count} message(s): {deleted_ids}"


class RuntimeMutationCommandsMixin(_CommandDependencies):
    """Legacy adapter exposing mutation commands on CommandHandler."""

    _runtime_mutation_commands: RuntimeMutationCommandHandlers

    async def rewind_messages(self, args: str) -> str:
        return await self._runtime_mutation_commands.rewind_messages(args)

    async def purge_messages(self, args: str) -> str:
        return await self._runtime_mutation_commands.purge_messages(args)
