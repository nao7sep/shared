"""Chat file management command mixin."""

from pathlib import Path

from ..chat import load_chat, save_chat
from ..chat_manager import (
    delete_chat as delete_chat_file,
    generate_chat_filename,
    rename_chat,
)
from ..logging_utils import sanitize_error_message
from .types import CommandResult, CommandSignal


class ChatFileCommandsMixin:
    @staticmethod
    def _is_yes_choice(answer: str) -> bool:
        return answer.strip().lower() in {"", "y", "yes"}

    @staticmethod
    def _is_no_choice(answer: str) -> bool:
        return answer.strip().lower() in {"n", "no"}

    async def new_chat(self, args: str) -> CommandResult:
        """Create new chat file.

        Args:
            args: Optional chat name

        Returns:
            Command text or typed new-chat control signal
        """
        chats_dir = self.manager.profile["chats_dir"]

        # Generate filename
        name = args.strip() if args else None
        new_path = generate_chat_filename(chats_dir, name)

        if not self.manager.chat_path:
            answer = await self._prompt_text(
                "No chat is open. Open the new chat now? [Y/n]: "
            )
            if self._is_no_choice(answer):
                # Persist the file so /open can select it later.
                await save_chat(new_path, load_chat(new_path))
                return f"Created new chat (not opened): {new_path}"
            if not self._is_yes_choice(answer):
                return "Cancelled"

        # Signal to REPL to switch to new chat.
        return CommandSignal(kind="new_chat", chat_path=new_path)

    async def open_chat(self, args: str) -> CommandResult:
        """Open existing chat file.

        Args:
            args: Optional filename or path

        Returns:
            Typed open-chat control signal or error message
        """
        chats_dir = self.manager.profile["chats_dir"]

        if args.strip():
            # Path provided as argument
            try:
                selected_path = self._resolve_chat_path_arg(args.strip(), chats_dir)
            except ValueError as e:
                return str(e)
        else:
            # Interactive selection
            selected_path = await self._prompt_chat_selection(
                chats_dir,
                action="open",
                allow_cancel=True,
            )

        if not selected_path:
            return "Chat open cancelled"

        # Verify file exists and is valid
        try:
            load_chat(selected_path)
        except Exception as e:
            return f"Error loading chat: {sanitize_error_message(str(e))}"

        # Signal to REPL to switch chat.
        return CommandSignal(kind="open_chat", chat_path=selected_path)

    async def switch_chat(self, args: str) -> CommandResult:
        """Switch to another chat file.

        Args:
            args: Optional filename or path (shows selection if empty)

        Returns:
            Typed open-chat control signal or error message
        """
        # Reuse /open behavior. The REPL loop saves current chat and opens selected one.
        return await self.open_chat(args)

    async def close_chat(self, args: str) -> CommandResult:
        """Close current chat.

        Args:
            args: Not used

        Returns:
            Typed close-chat control signal
        """
        if not self.manager.chat_path:
            return "No chat is currently open. Use /new or /open."

        # Signal to REPL to close chat
        return CommandSignal(kind="close_chat")

    async def rename_chat_file(self, args: str) -> CommandResult:
        """Rename a chat file.

        Args:
            args: "<target> <new_name>", where target is "current" or a chat name/path

        Returns:
            Command text or typed rename-current signal
        """
        chats_dir = self.manager.profile["chats_dir"]

        # Parse args
        parts = args.strip().split(None, 1)

        if not parts:
            # No args - prompt for chat to rename
            selected_path = await self._prompt_chat_selection(
                chats_dir, action="rename", allow_cancel=True
            )

            if not selected_path:
                return "Rename cancelled"

            new_name = (await self._prompt_text("Enter new name: ")).strip()
            if not new_name:
                return "Rename cancelled"

            # Perform rename
            try:
                new_path = rename_chat(selected_path, new_name, chats_dir)

                # Check if this was the current chat
                current_path = self.manager.chat_path
                if current_path and Path(current_path).resolve() == Path(selected_path).resolve():
                    # Signal to update current chat path
                    return CommandSignal(kind="rename_current", chat_path=new_path)
                else:
                    return f"Renamed: {Path(selected_path).name} → {Path(new_path).name}"

            except Exception as e:
                return f"Error renaming chat: {sanitize_error_message(str(e))}"

        if len(parts) < 2:
            return "Usage: /rename <chat_name|path|current> <new_name>"

        target, new_name = parts[0], parts[1].strip()
        if not new_name:
            return "Usage: /rename <chat_name|path|current> <new_name>"

        if target == "current":
            current_path = self.manager.chat_path
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
            current_path = self.manager.chat_path
            if current_path and Path(current_path).resolve() == old_path.resolve():
                return CommandSignal(kind="rename_current", chat_path=new_path)
            return f"Renamed: {old_path.name} → {Path(new_path).name}"

        except Exception as e:
            return f"Error renaming chat: {sanitize_error_message(str(e))}"

    async def delete_chat_command(self, args: str) -> CommandResult:
        """Delete a chat file.

        Args:
            args: Chat name/path, or "current"

        Returns:
            Command text or typed delete-current signal
        """
        chats_dir = self.manager.profile["chats_dir"]

        if not args.strip():
            # Interactive selection
            selected_path = await self._prompt_chat_selection(
                chats_dir, action="delete", allow_cancel=True
            )

            if not selected_path:
                return "Delete cancelled"
        else:
            # Parse argument
            name = args.strip()
            if name == "current":
                current_path = self.manager.chat_path
                if not current_path:
                    return "No chat is currently open. Use /new or /open."
                selected_path = current_path
            else:
                try:
                    selected_path = self._resolve_chat_path_arg(name, chats_dir)
                except ValueError as e:
                    return str(e)

        # Check if this is the current chat
        current_path = self.manager.chat_path
        is_current = (
            current_path
            and Path(current_path).resolve() == Path(selected_path).resolve()
        )

        # Confirm deletion
        print(f"\nWARNING: This will permanently delete: {Path(selected_path).name}")
        if not await self._confirm_yes("Type 'yes' to confirm deletion: "):
            return "Deletion cancelled"

        # Perform deletion
        try:
            delete_chat_file(selected_path)

            if is_current:
                # Signal to close current chat
                return CommandSignal(
                    kind="delete_current",
                    value=Path(selected_path).name,
                )
            else:
                return f"Deleted: {Path(selected_path).name}"

        except Exception as e:
            return f"Error deleting chat: {sanitize_error_message(str(e))}"
