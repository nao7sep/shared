"""Import-boundary guardrails for feature modules."""

from __future__ import annotations

import ast
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _iter_python_files(directory: Path) -> list[Path]:
    return sorted(path for path in directory.rglob("*.py") if path.is_file())


def _parse_ast(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _find_relative_parent_imports(
    tree: ast.AST,
    *,
    target_name: str,
) -> list[int]:
    lines: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.level < 2:
            continue
        if node.module == target_name:
            lines.append(node.lineno)
            continue
        if node.module is None and any(alias.name == target_name for alias in node.names):
            lines.append(node.lineno)
    return lines


def _find_absolute_module_imports(
    tree: ast.AST,
    *,
    module_name: str,
) -> list[int]:
    lines: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name == module_name for alias in node.names):
                lines.append(node.lineno)
            continue
        if isinstance(node, ast.ImportFrom) and node.module == module_name:
            lines.append(node.lineno)
    return lines


def test_orchestration_modules_do_not_import_root_orchestrator_facade() -> None:
    root = _repo_root()
    orchestration_dir = root / "src/polychat/orchestration"
    offenders: list[str] = []

    for path in _iter_python_files(orchestration_dir):
        tree = _parse_ast(path)
        lines = _find_relative_parent_imports(tree, target_name="orchestrator")
        lines.extend(
            _find_absolute_module_imports(
                tree,
                module_name="polychat.orchestrator",
            )
        )
        if lines:
            offenders.append(f"{path.relative_to(root)}:{','.join(str(line) for line in sorted(lines))}")

    assert not offenders, (
        "Orchestration modules must import chat/session feature packages directly, "
        "not root orchestrator facade: " + "; ".join(offenders)
    )


def test_command_modules_do_not_import_parent_commands_facade() -> None:
    root = _repo_root()
    commands_dir = root / "src/polychat/commands"
    offenders: list[str] = []

    for path in _iter_python_files(commands_dir):
        if path.name == "__init__.py":
            continue
        tree = _parse_ast(path)
        lines = _find_relative_parent_imports(tree, target_name="commands")
        lines.extend(
            _find_absolute_module_imports(
                tree,
                module_name="polychat.commands",
            )
        )
        if lines:
            offenders.append(f"{path.relative_to(root)}:{','.join(str(line) for line in sorted(lines))}")

    assert not offenders, (
        "Command modules must use explicit dependency wiring, not parent commands facade: "
        + "; ".join(offenders)
    )


def test_feature_modules_do_not_import_root_chat_manager_facade() -> None:
    root = _repo_root()
    src_dir = root / "src/polychat"
    offenders: list[str] = []

    for path in _iter_python_files(src_dir):
        if path.name == "chat_manager.py":
            continue
        tree = _parse_ast(path)
        lines = _find_relative_parent_imports(tree, target_name="chat_manager")
        lines.extend(
            _find_absolute_module_imports(
                tree,
                module_name="polychat.chat_manager",
            )
        )
        if lines:
            offenders.append(f"{path.relative_to(root)}:{','.join(str(line) for line in sorted(lines))}")

    assert not offenders, (
        "Feature modules must use chat package modules directly, not root chat_manager facade: "
        + "; ".join(offenders)
    )

