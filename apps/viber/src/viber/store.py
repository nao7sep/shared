"""JSON state file persistence."""

from __future__ import annotations

import json
from pathlib import Path

from .models import Database


def load_database(path: Path) -> Database:
    """Load database from JSON file. Returns an empty Database if file does not exist."""
    if not path.exists():
        return Database()
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    return Database.model_validate(data)


def save_database(db: Database, path: Path) -> None:
    """Serialize database to JSON and write to path.

    Uses indent=2 and preserves field declaration order.
    Creates parent directories if needed.
    Appends a trailing newline.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    data = db.model_dump(mode="json")
    text = json.dumps(data, indent=2, ensure_ascii=False)
    path.write_text(text + "\n", encoding="utf-8")
