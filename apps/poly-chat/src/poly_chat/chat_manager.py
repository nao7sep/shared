"""Chat file management utilities for PolyChat.

This module handles listing, selecting, creating, renaming, and deleting chat files.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Any


def list_chats(chats_dir: str) -> list[dict[str, Any]]:
    """List all chat files in the directory with metadata.

    Args:
        chats_dir: Absolute path to chats directory

    Returns:
        List of dicts with keys: filename, path, title, created_at, updated_at, message_count
        Sorted by updated_at (most recent first)
    """
    chats_path = Path(chats_dir)

    if not chats_path.exists():
        return []

    chat_files = []

    for file_path in chats_path.glob("*.json"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            metadata = data.get("metadata", {})
            messages = data.get("messages", [])

            chat_files.append({
                "filename": file_path.name,
                "path": str(file_path),
                "title": metadata.get("title"),
                "created_at": metadata.get("created_at"),
                "updated_at": metadata.get("updated_at"),
                "message_count": len(messages),
            })
        except Exception:
            # Skip invalid files
            continue

    # Sort by updated_at (most recent first), then by filename
    chat_files.sort(
        key=lambda x: (x["updated_at"] or "", x["filename"]),
        reverse=True
    )

    return chat_files


def format_chat_info(chat: dict[str, Any], index: int) -> str:
    """Format chat info for display in list.

    Args:
        chat: Chat dict from list_chats()
        index: Index in list (1-based for display)

    Returns:
        Formatted string for display
    """
    filename = chat["filename"]
    title = chat["title"] or "(no title)"
    msg_count = chat["message_count"]

    # Format updated time
    if chat["updated_at"]:
        try:
            dt = datetime.fromisoformat(chat["updated_at"])
            updated = dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            updated = "unknown"
    else:
        updated = "unknown"

    return f"{index:3}. {filename:40} | {title:30} | {msg_count:3} msgs | {updated}"


def prompt_chat_selection(
    chats_dir: str,
    action: str = "open",
    allow_cancel: bool = True
) -> Optional[str]:
    """Interactively prompt user to select a chat.

    Shows list of chats and allows:
    - Selection by number
    - Direct input of filename or path
    - Cancel (if allow_cancel=True)

    Args:
        chats_dir: Absolute path to chats directory
        action: Action name for prompts ("open", "rename", "delete")
        allow_cancel: Whether to allow cancellation

    Returns:
        Absolute path to selected chat, or None if cancelled
    """
    chats = list_chats(chats_dir)

    if not chats:
        print(f"No chat files found in: {chats_dir}")
        path_input = input(f"\nEnter path to {action} (or press Enter to cancel): ").strip()
        if not path_input:
            return None
        return path_input

    # Display list
    print(f"\nAvailable chats in: {chats_dir}")
    print("=" * 100)
    print(f"     {'Filename':<40} | {'Title':<30} | Messages | Last Updated")
    print("-" * 100)

    for i, chat in enumerate(chats, 1):
        print(format_chat_info(chat, i))

    print("=" * 100)

    # Prompt for selection
    if allow_cancel:
        prompt = f"\nSelect chat to {action} (number, filename, or path) [Enter to cancel]: "
    else:
        prompt = f"\nSelect chat to {action} (number, filename, or path): "

    while True:
        selection = input(prompt).strip()

        if not selection:
            if allow_cancel:
                return None
            else:
                print("Selection required.")
                continue

        # Try as number
        try:
            index = int(selection)
            if 1 <= index <= len(chats):
                return chats[index - 1]["path"]
            else:
                print(f"Invalid number. Choose 1-{len(chats)}")
                continue
        except ValueError:
            pass

        # Try as filename (look in chats_dir)
        if not selection.startswith("/") and not selection.startswith("~"):
            # Relative filename - check in chats_dir
            candidate = Path(chats_dir) / selection
            if candidate.exists():
                return str(candidate)

            # Add .json if missing
            if not selection.endswith(".json"):
                candidate = Path(chats_dir) / f"{selection}.json"
                if candidate.exists():
                    return str(candidate)

        # Try as absolute path or path with ~
        path = Path(selection).expanduser()
        if path.exists():
            return str(path)

        # Not found
        print(f"Chat not found: {selection}")
        print("Try again or press Enter to cancel.")


def generate_chat_filename(chats_dir: str, name: Optional[str] = None) -> str:
    """Generate a new chat filename.

    Args:
        chats_dir: Absolute path to chats directory
        name: Optional base name (will be sanitized)

    Returns:
        Absolute path to new chat file (guaranteed not to exist)
    """
    if name:
        # Sanitize name
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
        base = f"{safe_name}.json"
    else:
        # Use timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = f"chat_{timestamp}.json"

    candidate = Path(chats_dir) / base

    # If exists, add counter
    if candidate.exists():
        counter = 1
        stem = candidate.stem
        while candidate.exists():
            if name:
                candidate = Path(chats_dir) / f"{stem}_{counter}.json"
            else:
                candidate = Path(chats_dir) / f"chat_{timestamp}_{counter}.json"
            counter += 1

    return str(candidate)


def rename_chat(old_path: str, new_name: str, chats_dir: str) -> str:
    """Rename a chat file.

    Args:
        old_path: Absolute path to existing chat file
        new_name: New filename (can be just basename or full path)
        chats_dir: Absolute path to chats directory

    Returns:
        Absolute path to renamed file

    Raises:
        FileNotFoundError: If old file doesn't exist
        FileExistsError: If new file already exists
    """
    old_file = Path(old_path)

    if not old_file.exists():
        raise FileNotFoundError(f"Chat file not found: {old_path}")

    # Determine new path
    if "/" in new_name or new_name.startswith("~"):
        # Full path provided
        new_file = Path(new_name).expanduser()
    else:
        # Just filename - put in chats_dir
        if not new_name.endswith(".json"):
            new_name = f"{new_name}.json"
        new_file = Path(chats_dir) / new_name

    if new_file.exists():
        raise FileExistsError(f"Chat file already exists: {new_file}")

    # Rename
    old_file.rename(new_file)

    return str(new_file)


def delete_chat(path: str) -> None:
    """Delete a chat file.

    Args:
        path: Absolute path to chat file

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    chat_file = Path(path)

    if not chat_file.exists():
        raise FileNotFoundError(f"Chat file not found: {path}")

    # Confirm deletion
    print(f"\nWARNING: This will permanently delete: {chat_file.name}")
    confirm = input("Type 'yes' to confirm deletion: ").strip().lower()

    if confirm != "yes":
        raise ValueError("Deletion cancelled")

    chat_file.unlink()
