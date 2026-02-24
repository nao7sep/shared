#!/usr/bin/env python3
"""Generate the README in-chat commands section from command metadata."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


def _load_command_docs():
    module_path = Path(__file__).resolve().parents[1] / "src/polychat/commands/command_docs.py"
    module_dir = module_path.parent
    if str(module_dir) not in sys.path:
        sys.path.insert(0, str(module_dir))
    spec = importlib.util.spec_from_file_location(
        "polychat_command_docs_generator",
        module_path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module spec from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    return (
        module.README_COMMANDS_BEGIN_MARKER,
        module.README_COMMANDS_END_MARKER,
        module.render_readme_commands_block(),
    )


def main() -> int:
    readme_path = Path(__file__).resolve().parents[1] / "README.md"
    readme_text = readme_path.read_text(encoding="utf-8")

    begin_marker, end_marker, generated_block = _load_command_docs()

    begin = readme_text.find(begin_marker)
    end = readme_text.find(end_marker)
    if begin < 0 or end < 0 or end < begin:
        raise RuntimeError("README generated command markers not found or malformed")

    end += len(end_marker)
    updated = readme_text[:begin] + generated_block + readme_text[end:]

    if updated != readme_text:
        readme_path.write_text(updated, encoding="utf-8")
        print(f"Updated {readme_path}")
    else:
        print(f"No changes: {readme_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
