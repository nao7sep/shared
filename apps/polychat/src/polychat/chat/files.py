"""Chat file listing and filesystem operations."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path, PureWindowsPath
from typing import Any, Callable, Optional

from ..constants import APP_NAME, CHAT_FILE_EXTENSION, DATETIME_FORMAT_FILENAME
from ..path_utils import has_app_path_prefix, has_home_path_prefix, map_path


def _is_windows_absolute_path(path: str) -> bool:
    """Return True for Windows absolute paths on any platform."""
    return PureWindowsPath(path).is_absolute()


def _is_windows_drive_relative_path(path: str) -> bool:
    """Return True for drive-relative Windows paths like C:temp."""
    win_path = PureWindowsPath(path)
    return bool(win_path.drive) and not win_path.is_absolute()


def list_chats(chats_dir: str) -> list[dict[str, Any]]:
    """List all chat files in the directory with metadata."""
    chats_path = Path(chats_dir)

    if not chats_path.exists():
        return []

    chat_files = []

    for file_path in chats_path.glob(f"*{CHAT_FILE_EXTENSION}"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            metadata = data.get("metadata", {})
            messages = data.get("messages", [])

            chat_files.append(
                {
                    "filename": file_path.name,
                    "path": str(file_path),
                    "title": metadata.get("title"),
                    "created_at": metadata.get("created_at"),
                    "updated_at": metadata.get("updated_at"),
                    "message_count": len(messages),
                }
            )
        except Exception as e:
            # Skip invalid files but log the issue.
            logging.debug(f"Skipping invalid chat file {file_path}: {e}")
            continue

    # Sort by updated_at (most recent first), then by filename.
    chat_files.sort(key=lambda x: (x["updated_at"] or "", x["filename"]), reverse=True)

    return chat_files


def generate_chat_filename(chats_dir: str, name: Optional[str] = None) -> str:
    """Generate a new chat filename."""
    if name:
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
        base = f"{safe_name}{CHAT_FILE_EXTENSION}"
    else:
        timestamp = datetime.now().strftime(DATETIME_FORMAT_FILENAME)
        base = f"{APP_NAME}_{timestamp}{CHAT_FILE_EXTENSION}"

    candidate = Path(chats_dir) / base

    if candidate.exists():
        counter = 1
        stem = candidate.stem
        while candidate.exists():
            if name:
                candidate = Path(chats_dir) / f"{stem}_{counter}{CHAT_FILE_EXTENSION}"
            else:
                candidate = (
                    Path(chats_dir) / f"{APP_NAME}_{timestamp}_{counter}{CHAT_FILE_EXTENSION}"
                )
            counter += 1

    return str(candidate)


def rename_chat(old_path: str, new_name: str, chats_dir: str) -> str:
    """Rename a chat file."""
    return _rename_chat(old_path, new_name, chats_dir)


def _rename_chat(
    old_path: str,
    new_name: str,
    chats_dir: str,
    *,
    map_path_fn: Callable[[str], str] = map_path,
) -> str:
    """Rename a chat file.

    map_path_fn exists for compatibility wrappers/tests that monkeypatch
    the path mapper at the old `polychat.chat_manager` module boundary.
    """
    old_file = Path(old_path)

    if not old_file.exists():
        raise FileNotFoundError(f"Chat file not found: {old_path}")

    if _is_windows_drive_relative_path(new_name):
        raise ValueError(
            f"Invalid path: {new_name} (Windows drive-relative paths are not supported)"
        )

    chats_dir_resolved = Path(chats_dir).resolve()

    is_native_absolute = Path(new_name).is_absolute()
    is_windows_absolute = _is_windows_absolute_path(new_name)
    is_absolute = is_native_absolute or is_windows_absolute
    is_mapped_path = has_home_path_prefix(new_name) or has_app_path_prefix(new_name)
    is_path_like = "/" in new_name or "\\" in new_name or is_mapped_path or is_absolute

    if is_path_like:
        if is_windows_absolute and not is_native_absolute:
            raise ValueError(
                f"Invalid path: {new_name} (Windows absolute paths are not supported on this platform)"
            )

        if is_mapped_path:
            new_file = Path(map_path_fn(new_name))
        else:
            new_file = Path(new_name).expanduser()

        if is_absolute or is_mapped_path:
            new_file = new_file.resolve()
        else:
            new_file = (Path(chats_dir) / new_name).resolve()
            try:
                new_file.relative_to(chats_dir_resolved)
            except ValueError:
                raise ValueError(f"Invalid path: {new_name} (outside chats directory)")
    else:
        if not new_name.endswith(CHAT_FILE_EXTENSION):
            new_name = f"{new_name}{CHAT_FILE_EXTENSION}"
        new_file = (Path(chats_dir) / new_name).resolve()

        try:
            new_file.relative_to(chats_dir_resolved)
        except ValueError:
            raise ValueError(f"Invalid filename: {new_name} (outside chats directory)")

    if new_file.exists():
        raise FileExistsError(f"Chat file already exists: {new_file}")

    old_file.rename(new_file)

    return str(new_file)


def delete_chat(path: str) -> None:
    """Delete a chat file."""
    chat_file = Path(path)

    if not chat_file.exists():
        raise FileNotFoundError(f"Chat file not found: {path}")

    chat_file.unlink()
