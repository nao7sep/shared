"""Chat file management command mixin."""

from pathlib import Path

from ..chat import load_chat, save_chat
from ..chat_manager import (
    delete_chat as delete_chat_file,
    generate_chat_filename,
    rename_chat,
)
from ..ui.chat_ui import prompt_chat_selection


class ChatFileCommandsMixin:
    async def new_chat(self, args: str) -> str:
        """Create new chat file.

        Args:
            args: Optional chat name

        Returns:
            Confirmation message or special __NEW_CHAT__ signal
        """
        chats_dir = self.manager.profile["chats_dir"]

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
        chats_dir = self.manager.profile["chats_dir"]

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
        if not self.manager.chat_path:
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
        chats_dir = self.manager.profile["chats_dir"]

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
                current_path = self.manager.chat_path
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
        chats_dir = self.manager.profile["chats_dir"]

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
                current_path = self.manager.chat_path
                if not current_path:
                    return "No chat is currently open"
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
        confirm = input("Type 'yes' to confirm deletion: ").strip().lower()

        if confirm != "yes":
            return "Deletion cancelled"

        # Perform deletion
        try:
            delete_chat_file(selected_path)

            if is_current:
                # Signal to close current chat
                return f"__DELETE_CURRENT__:{Path(selected_path).name}"
            else:
                return f"Deleted: {Path(selected_path).name}"

        except Exception as e:
            return f"Error deleting chat: {e}"
