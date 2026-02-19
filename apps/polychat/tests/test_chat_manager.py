"""Tests for chat_manager module."""

import json
import pytest
from pathlib import Path
from polychat.chat_manager import (
    list_chats,
    generate_chat_filename,
    rename_chat,
)
from polychat.ui.chat_ui import format_chat_info


def test_list_chats_empty_directory(tmp_path):
    """Test listing chats in empty directory."""
    chats = list_chats(str(tmp_path))
    assert chats == []


def test_list_chats_nonexistent_directory():
    """Test listing chats in non-existent directory."""
    chats = list_chats("/nonexistent/path")
    assert chats == []


def test_list_chats_single_valid_file(tmp_path):
    """Test listing single valid chat file."""
    chat_file = tmp_path / "test-chat.json"
    chat_data = {
        "metadata": {
            "title": "Test Chat",
            "summary": None,
            "system_prompt": None,
            "created_at": "2026-02-02T00:00:00+00:00",
            "updated_at": "2026-02-02T12:00:00+00:00",
        },
        "messages": [
            {"timestamp": "2026-02-02T00:00:00+00:00", "role": "user", "content": ["Hello"]},
            {"timestamp": "2026-02-02T00:00:01+00:00", "role": "assistant", "model": "test-model", "content": ["Hi"]},
        ]
    }
    chat_file.write_text(json.dumps(chat_data))

    chats = list_chats(str(tmp_path))

    assert len(chats) == 1
    assert chats[0]["filename"] == "test-chat.json"
    assert chats[0]["title"] == "Test Chat"
    assert chats[0]["message_count"] == 2
    assert chats[0]["updated_at"] == "2026-02-02T12:00:00+00:00"


def test_list_chats_multiple_files_sorted(tmp_path):
    """Test listing multiple files sorted by updated_at."""
    # Create three chat files with different timestamps
    for i, (name, updated) in enumerate([
        ("old.json", "2026-02-02T00:00:00+00:00"),
        ("new.json", "2026-02-04T00:00:00+00:00"),
        ("middle.json", "2026-02-03T00:00:00+00:00"),
    ]):
        chat_file = tmp_path / name
        chat_data = {
            "metadata": {
                "title": f"Chat {i}",
                "summary": None,
                "system_prompt": None,
                "created_at": updated,
                "updated_at": updated,
            },
            "messages": []
        }
        chat_file.write_text(json.dumps(chat_data))

    chats = list_chats(str(tmp_path))

    # Should be sorted by updated_at (most recent first)
    assert len(chats) == 3
    assert chats[0]["filename"] == "new.json"
    assert chats[1]["filename"] == "middle.json"
    assert chats[2]["filename"] == "old.json"


def test_list_chats_missing_metadata(tmp_path):
    """Test listing with file missing metadata field."""
    chat_file = tmp_path / "incomplete.json"
    chat_data = {
        "messages": []
        # Missing metadata
    }
    chat_file.write_text(json.dumps(chat_data))

    chats = list_chats(str(tmp_path))

    # Should handle gracefully with None values
    assert len(chats) == 1
    assert chats[0]["title"] is None
    assert chats[0]["updated_at"] is None


def test_list_chats_invalid_json(tmp_path):
    """Test listing with invalid JSON file."""
    valid_file = tmp_path / "valid.json"
    valid_file.write_text(json.dumps({"metadata": {}, "messages": []}))

    invalid_file = tmp_path / "invalid.json"
    invalid_file.write_text("{ invalid json }")

    chats = list_chats(str(tmp_path))

    # Should skip invalid file
    assert len(chats) == 1
    assert chats[0]["filename"] == "valid.json"


def test_list_chats_ignores_non_json_files(tmp_path):
    """Test that non-JSON files are ignored."""
    # Create JSON file
    json_file = tmp_path / "chat.json"
    json_file.write_text(json.dumps({"metadata": {}, "messages": []}))

    # Create non-JSON files
    (tmp_path / "readme.txt").write_text("text file")
    (tmp_path / "data.csv").write_text("csv file")

    chats = list_chats(str(tmp_path))

    # Should only find JSON file
    assert len(chats) == 1
    assert chats[0]["filename"] == "chat.json"


def test_format_chat_info_with_title():
    """Test formatting chat info with title."""
    chat = {
        "filename": "test-chat.json",
        "title": "My Important Chat",
        "message_count": 42,
        "updated_at": "2026-02-08T14:30:00+00:00",
    }

    formatted = format_chat_info(chat, 1)

    assert "[1]" in formatted
    assert "test-chat.json" in formatted
    assert "My Important Chat" in formatted
    assert "| 42 msgs |" in formatted
    # Check date is present (time will vary by timezone, so just check date part)
    assert "2026-02-08" in formatted


def test_format_chat_info_no_title():
    """Test formatting chat info without title."""
    chat = {
        "filename": "untitled.json",
        "title": None,
        "message_count": 0,
        "updated_at": None,
    }

    formatted = format_chat_info(chat, 5)

    assert "[5]" in formatted
    assert "(no title)" not in formatted
    assert "| 0 msgs | unknown" in formatted
    assert "\n" not in formatted
    assert "unknown" in formatted


def test_format_chat_info_invalid_timestamp():
    """Test formatting with invalid timestamp."""
    chat = {
        "filename": "test.json",
        "title": "Test",
        "message_count": 1,
        "updated_at": "invalid-timestamp",
    }

    formatted = format_chat_info(chat, 1)

    assert "unknown" in formatted


def test_generate_chat_filename_with_name(tmp_path):
    """Test generating chat filename with custom name."""
    path = generate_chat_filename(str(tmp_path), "my-project")

    assert path.endswith("my-project.json")
    assert str(tmp_path) in path


def test_generate_chat_filename_without_name(tmp_path):
    """Test generating chat filename with timestamp."""
    path = generate_chat_filename(str(tmp_path))

    # Should match pattern: polychat_YYYY-MM-DD_HH-MM-SS.json
    filename = Path(path).name
    assert filename.startswith("polychat_")
    assert filename.endswith(".json")

    # Extract timestamp part
    timestamp_part = filename[9:-5]  # Remove "polychat_" (9 chars) and ".json"

    # Should have format: YYYY-MM-DD_HH-MM-SS
    parts = timestamp_part.split("_")
    assert len(parts) == 2
    assert len(parts[0]) == 10  # YYYY-MM-DD
    assert len(parts[1]) == 8   # HH-MM-SS


def test_generate_chat_filename_sanitizes_name(tmp_path):
    """Test that special characters are sanitized."""
    path = generate_chat_filename(str(tmp_path), "my/project:name*")

    filename = Path(path).name
    # Should replace special chars with underscore
    assert "/" not in filename
    assert ":" not in filename
    assert "*" not in filename
    assert "my_project_name" in filename


def test_generate_chat_filename_handles_collision(tmp_path):
    """Test collision handling with counter."""
    # Create existing file
    name = "test-chat"
    existing = tmp_path / f"{name}.json"
    existing.write_text("{}")

    # Generate new filename - should add counter
    path = generate_chat_filename(str(tmp_path), name)

    filename = Path(path).name
    assert filename == "test-chat_1.json"


def test_generate_chat_filename_multiple_collisions(tmp_path):
    """Test multiple collisions."""
    # Create multiple existing files
    (tmp_path / "chat.json").write_text("{}")
    (tmp_path / "chat_1.json").write_text("{}")
    (tmp_path / "chat_2.json").write_text("{}")

    path = generate_chat_filename(str(tmp_path), "chat")

    filename = Path(path).name
    assert filename == "chat_3.json"


def test_rename_chat_simple(tmp_path):
    """Test simple chat rename."""
    old_file = tmp_path / "old-name.json"
    old_file.write_text("{}")

    new_path = rename_chat(str(old_file), "new-name", str(tmp_path))

    assert not old_file.exists()
    assert Path(new_path).exists()
    assert Path(new_path).name == "new-name.json"


def test_rename_chat_adds_json_extension(tmp_path):
    """Test that .json extension is added if missing."""
    old_file = tmp_path / "old.json"
    old_file.write_text("{}")

    new_path = rename_chat(str(old_file), "new-name-no-ext", str(tmp_path))

    assert Path(new_path).name == "new-name-no-ext.json"


def test_rename_chat_with_full_path(tmp_path):
    """Test rename with full path."""
    old_file = tmp_path / "old.json"
    old_file.write_text("{}")

    new_dir = tmp_path / "subdir"
    new_dir.mkdir()
    new_full_path = new_dir / "moved.json"

    new_path = rename_chat(str(old_file), str(new_full_path), str(tmp_path))

    assert not old_file.exists()
    assert Path(new_path).exists()
    assert str(new_full_path) == new_path


def test_rename_chat_supports_app_mapped_path(tmp_path, monkeypatch):
    """Mapped @/ paths are resolved via path_utils.map_path."""
    old_file = tmp_path / "old.json"
    old_file.write_text("{}")

    mapped_dir = tmp_path / "mapped"
    mapped_dir.mkdir()
    mapped_target = mapped_dir / "renamed.json"

    called = {}

    def fake_map_path(path: str) -> str:
        called["path"] = path
        return str(mapped_target)

    monkeypatch.setattr("polychat.chat_manager.map_path", fake_map_path)

    new_path = rename_chat(str(old_file), "@/renamed.json", str(tmp_path))

    assert called["path"] == "@/renamed.json"
    assert Path(new_path).exists()
    assert str(mapped_target) == new_path
    assert not old_file.exists()


def test_rename_chat_rejects_windows_absolute_path_on_non_windows(tmp_path):
    """Windows absolute paths should not be treated as chats_dir-relative names."""
    if Path("C:/").exists():
        pytest.skip("Windows-specific non-Windows guard")

    old_file = tmp_path / "old.json"
    old_file.write_text("{}")

    with pytest.raises(ValueError, match="Windows absolute paths are not supported"):
        rename_chat(str(old_file), r"C:\\Users\\alice\\renamed.json", str(tmp_path))

    assert old_file.exists()


def test_rename_chat_nonexistent_file(tmp_path):
    """Test renaming non-existent file raises error."""
    with pytest.raises(FileNotFoundError, match="Chat file not found"):
        rename_chat(str(tmp_path / "nonexistent.json"), "new", str(tmp_path))


def test_rename_chat_target_exists(tmp_path):
    """Test renaming to existing file raises error."""
    old_file = tmp_path / "old.json"
    old_file.write_text("{}")

    existing = tmp_path / "existing.json"
    existing.write_text("{}")

    with pytest.raises(FileExistsError, match="Chat file already exists"):
        rename_chat(str(old_file), "existing.json", str(tmp_path))


def test_rename_chat_preserves_content(tmp_path):
    """Test that rename preserves file content."""
    old_file = tmp_path / "old.json"
    content = {"test": "data", "nested": {"value": 123}}
    old_file.write_text(json.dumps(content))

    new_path = rename_chat(str(old_file), "new", str(tmp_path))

    # Verify content preserved
    with open(new_path, "r") as f:
        loaded = json.load(f)

    assert loaded == content
