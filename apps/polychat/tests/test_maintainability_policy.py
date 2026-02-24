"""Policy checks to prevent new maintainability debt."""

from __future__ import annotations

from pathlib import Path


MAX_MODULE_LINES = 500

REFORMATTED_TYPED_TARGETS = (
    "src/polychat/commands/command_docs.py",
    "src/polychat/commands/command_docs_data.py",
    "src/polychat/ai/provider_logging.py",
    "src/polychat/ai/provider_utils.py",
    "src/polychat/logging/schema.py",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _line_count(path: Path) -> int:
    with path.open(encoding="utf-8") as fh:
        return sum(1 for _ in fh)


def test_no_polychat_module_exceeds_size_threshold() -> None:
    root = _repo_root()
    oversized: list[tuple[str, int]] = []

    for path in sorted((root / "src/polychat").rglob("*.py")):
        lines = _line_count(path)
        if lines > MAX_MODULE_LINES:
            oversized.append((str(path.relative_to(root)), lines))

    assert not oversized, (
        "Modules exceed 500-line threshold (add split rationale before merge): "
        + ", ".join(f"{path} ({lines})" for path, lines in oversized)
    )


def test_refactored_typed_targets_avoid_dict_any() -> None:
    root = _repo_root()
    offenders: list[str] = []

    for rel_path in REFORMATTED_TYPED_TARGETS:
        text = (root / rel_path).read_text(encoding="utf-8")
        if "dict[str, Any]" in text:
            offenders.append(rel_path)

    assert not offenders, (
        "Refactored typed targets reintroduced dict[str, Any]: " + ", ".join(offenders)
    )
