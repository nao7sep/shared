"""Prompt session and key-binding setup for the PolyChat REPL."""

from __future__ import annotations

from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings

from ..constants import REPL_HISTORY_FILE
from ..path_utils import map_path
from ..session_manager import SessionManager


def build_key_bindings(manager: SessionManager) -> KeyBindings:
    """Build key bindings for quick/compose input modes."""
    key_bindings = KeyBindings()

    @key_bindings.add("enter", eager=True)
    def _handle_enter(event) -> None:
        mode = manager.input_mode
        if mode == "quick":
            buffer_text = event.current_buffer.text
            if buffer_text and buffer_text.strip():
                event.current_buffer.validate_and_handle()
            elif buffer_text and not buffer_text.strip():
                event.current_buffer.reset()
        else:
            event.current_buffer.insert_text("\n")

    @key_bindings.add("escape", "enter", eager=True)
    def _handle_alt_enter(event) -> None:
        mode = manager.input_mode
        if mode == "quick":
            event.current_buffer.insert_text("\n")
        else:
            event.current_buffer.validate_and_handle()

    @key_bindings.add("c-j", eager=True)
    def _handle_ctrl_j(event) -> None:
        event.current_buffer.validate_and_handle()

    return key_bindings


def ensure_history_file() -> Path:
    """Ensure the REPL history file path exists and return it."""
    history_file = Path(map_path(REPL_HISTORY_FILE))
    history_file.parent.mkdir(parents=True, exist_ok=True)
    return history_file


def create_prompt_session(manager: SessionManager) -> PromptSession:
    """Create prompt-toolkit session for REPL input."""
    history_file = ensure_history_file()
    return PromptSession(
        history=FileHistory(str(history_file)),
        key_bindings=build_key_bindings(manager),
        multiline=True,
    )
