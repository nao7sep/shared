"""Backward-compatible facade for chat file management utilities."""

from .chat.files import (
    _rename_chat,
    delete_chat,
    generate_chat_filename,
    list_chats,
)
from .path_utils import map_path


def rename_chat(old_path: str, new_name: str, chats_dir: str) -> str:
    """Compatibility wrapper preserving monkeypatchable map_path behavior."""
    return _rename_chat(old_path, new_name, chats_dir, map_path_fn=map_path)


__all__ = [
    "list_chats",
    "generate_chat_filename",
    "rename_chat",
    "delete_chat",
]

