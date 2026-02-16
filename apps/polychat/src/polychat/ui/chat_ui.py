"""Chat UI presentation and interaction functions."""

from typing import Any, Optional

from ..chat_manager import list_chats
from ..text_formatting import format_chat_list_item, make_borderline


def format_chat_info(chat: dict[str, Any], index: int) -> str:
    """Format one chat record for display in list."""
    return format_chat_list_item(chat, index)


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
    print(make_borderline())

    for i, chat in enumerate(chats, 1):
        print(format_chat_info(chat, i))

    print(make_borderline())

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
