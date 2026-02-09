"""Interactive prompt collection for tk REPL."""

from typing import Any

from tk.validation import validate_date_format


def collect_done_cancel_prompts(
    task: dict[str, Any],
    status: str,
    default_date: str,
    provided_note: str | None = None,
    provided_date: str | None = None,
) -> dict[str, Any] | str:
    """Collect interactive prompts for done/cancel commands.

    Args:
        task: Task dictionary being handled
        status: "done" or "cancelled"
        default_date: Default subjective date to use
        provided_note: Note already provided via --note flag
        provided_date: Date already provided via --date flag

    Returns:
        Dictionary with "note" and "date" keys, or "CANCELLED" string if user cancels

    Raises:
        KeyboardInterrupt: If user presses Ctrl+C (caller should handle)
    """
    print(f"Task: {task['text']}")
    print(f"Will be marked as: {status}")
    print(f"Subjective date: {default_date}")
    print("(Press Ctrl+C to cancel)")

    result = {}

    try:
        # Collect note if not provided
        if provided_note is None:
            note_input = input("Note (press Enter to skip): ").strip()
            result["note"] = note_input if note_input else None
        else:
            result["note"] = provided_note

        # Collect date if not provided
        if provided_date is None:
            date_input = input(f"Date override (press Enter to use {default_date}): ").strip()
            if date_input:
                validate_date_format(date_input)
                result["date"] = date_input
            else:
                result["date"] = default_date
        else:
            result["date"] = provided_date

        return result

    except KeyboardInterrupt:
        print()
        return "CANCELLED"


def collect_delete_confirmation(task: dict[str, Any]) -> bool:
    """Collect confirmation for delete command.

    Args:
        task: Task dictionary being deleted

    Returns:
        True if user confirms deletion, False otherwise
    """
    print(f"Task: {task['text']}")
    print(f"Status: {task['status']}")

    confirm = input("Delete permanently? (yes/N): ").strip().lower()
    return confirm == "yes"
