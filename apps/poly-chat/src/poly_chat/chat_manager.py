"""Chat file management utilities for PolyChat.

This module handles listing, selecting, creating, renaming, and deleting chat files.
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timezone
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
        except Exception as e:
            # Skip invalid files but log the issue
            logging.debug(f"Skipping invalid chat file {file_path}: {e}")
            continue

    # Sort by updated_at (most recent first), then by filename
    chat_files.sort(
        key=lambda x: (x["updated_at"] or "", x["filename"]),
        reverse=True
    )

    return chat_files


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
        # Use timestamp: poly-chat_YYYY-MM-DD_HH-MM-SS.json
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        base = f"poly-chat_{timestamp}.json"

    candidate = Path(chats_dir) / base

    # If exists, add counter (rare case)
    if candidate.exists():
        counter = 1
        stem = candidate.stem
        while candidate.exists():
            if name:
                candidate = Path(chats_dir) / f"{stem}_{counter}.json"
            else:
                candidate = Path(chats_dir) / f"poly-chat_{timestamp}_{counter}.json"
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
    chats_dir_resolved = Path(chats_dir).resolve()

    if "/" in new_name or new_name.startswith("~"):
        # Full path provided
        new_file = Path(new_name).expanduser().resolve()

        # Security check: If it looks like a relative path, validate it's within chats_dir
        if not Path(new_name).is_absolute() and not new_name.startswith("~"):
            try:
                new_file.relative_to(chats_dir_resolved)
            except ValueError:
                raise ValueError(f"Invalid path: {new_name} (outside chats directory)")
    else:
        # Just filename - put in chats_dir
        if not new_name.endswith(".json"):
            new_name = f"{new_name}.json"
        new_file = (Path(chats_dir) / new_name).resolve()

        # Security check: Ensure resolved path is within chats_dir
        try:
            new_file.relative_to(chats_dir_resolved)
        except ValueError:
            raise ValueError(f"Invalid filename: {new_name} (outside chats directory)")

    if new_file.exists():
        raise FileExistsError(f"Chat file already exists: {new_file}")

    # Rename
    old_file.rename(new_file)

    return str(new_file)


def delete_chat(path: str) -> None:
    """Delete a chat file.

    Note: Caller is responsible for user confirmation before calling this function.

    Args:
        path: Absolute path to chat file

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    chat_file = Path(path)

    if not chat_file.exists():
        raise FileNotFoundError(f"Chat file not found: {path}")

    chat_file.unlink()
