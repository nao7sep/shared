"""Chat UI presentation and interaction functions."""

from datetime import datetime, timezone
from typing import Any, Optional

from ..chat_manager import list_chats


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
            dt = datetime.fromisoformat(chat["updated_at"].replace("Z", "+00:00"))
            if dt.tzinfo is None:
                # Internal timestamps are UTC; assume UTC if tz is missing.
                dt = dt.replace(tzinfo=timezone.utc)
            updated = dt.astimezone().strftime("%Y-%m-%d %H:%M")
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
    """Interactively prompt user to select a chat from a list.

    Shows numbered list of chats. User selects by number only.
    For direct path input, use the command with an argument instead.

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
        return None

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
        prompt = f"\nSelect chat number to {action} [Enter to cancel]: "
    else:
        prompt = f"\nSelect chat number to {action}: "

    while True:
        selection = input(prompt).strip()

        if not selection:
            if allow_cancel:
                return None
            else:
                print("Selection required.")
                continue

        # Only accept numbers
        try:
            index = int(selection)
            if 1 <= index <= len(chats):
                return chats[index - 1]["path"]
            else:
                print(f"Invalid number. Choose 1-{len(chats)}")
                continue
        except ValueError:
            if allow_cancel:
                print(f"Please enter a number (1-{len(chats)}) or press Enter to cancel")
            else:
                print(f"Please enter a number (1-{len(chats)})")
            continue
