"""Interactive prompt collection for tk REPL."""

from tk.models import DoneCancelResult, Task, TaskStatus
from tk.validation import validate_date_format


def collect_done_cancel_prompts(
    task: Task,
    status: TaskStatus,
    default_date: str,
) -> DoneCancelResult | str:
    """Collect interactive prompts for done/cancel commands.

    Args:
        task: Task being handled
        status: "done" or "cancelled"
        default_date: Default subjective date to use
    Returns:
        DoneCancelResult with note and date, or "CANCELLED" string if user cancels

    Raises:
        KeyboardInterrupt: If user presses Ctrl+C (caller should handle)
    """
    print(f"Task: {task.text}")
    print(f"Will be marked as: {status.value}")
    print(f"Subjective date: {default_date}")
    print("(Press Ctrl+C to cancel)")

    try:
        note_input = input("Note (press Enter to skip): ").strip()
        note = note_input if note_input else None

        date_input = input(f"Date override (press Enter to use {default_date}): ").strip()
        if date_input:
            validate_date_format(date_input)
            date = date_input
        else:
            date = default_date

        return DoneCancelResult(note=note, date=date)

    except KeyboardInterrupt:
        print()
        return "CANCELLED"


def collect_delete_confirmation(task: Task) -> bool:
    """Collect confirmation for delete command.

    Args:
        task: Task being deleted

    Returns:
        True if user confirms deletion, False otherwise
    """
    print(f"Task: {task.text}")
    print(f"Status: {task.status}")

    confirm = input("Delete permanently? (yes/N): ").strip().lower()
    return confirm == "yes"
