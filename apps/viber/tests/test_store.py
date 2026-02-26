"""Tests for JSON persistence."""

import json
from pathlib import Path

from viber.models import Database, Group
from viber.store import load_database, save_database


def test_load_missing_file(tmp_path: Path) -> None:
    path = tmp_path / "data.json"
    db = load_database(path)
    assert isinstance(db, Database)
    assert db.groups == []


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "data.json"
    db = Database()
    db.groups.append(Group(id=1, name="Backend"))
    db.next_group_id = 2
    save_database(db, path)

    restored = load_database(path)
    assert len(restored.groups) == 1
    assert restored.groups[0].name == "Backend"
    assert restored.next_group_id == 2


def test_save_creates_parent_dirs(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "dir" / "data.json"
    db = Database()
    save_database(db, path)
    assert path.exists()


def test_save_trailing_newline(tmp_path: Path) -> None:
    path = tmp_path / "data.json"
    save_database(Database(), path)
    content = path.read_text(encoding="utf-8")
    assert content.endswith("\n")


def test_save_valid_json(tmp_path: Path) -> None:
    path = tmp_path / "data.json"
    db = Database()
    db.groups.append(Group(id=1, name="Test"))
    save_database(db, path)
    content = path.read_text(encoding="utf-8")
    parsed = json.loads(content)
    assert "groups" in parsed
    assert parsed["groups"][0]["name"] == "Test"
