# No New Debt Policy

## Purpose

Prevent maintainability regressions while refactoring continues.

## Rules

1. No new oversized modules:
   - Any new or modified Python module under `src/polychat/` must stay at or below 500 lines.
   - If a module must exceed 500 lines, add an explicit split-rationale note in architecture docs before merge.

2. No new untyped core-shape debt in refactored paths:
   - Avoid introducing new `dict[str, Any]` in refactored core modules.
   - Prefer typed models, typed mappings, or narrow value unions.

3. Keep staged strict typing for low-coupling refactored modules:
   - Run strict staged gate:
     - `scripts/check-mypy-staged.command`
   - This gate runs:
     - `mypy --strict --follow-imports=skip` on selected refactored modules.

## Enforcement

- `tests/test_maintainability_policy.py` enforces module-size and typed-debt checks for refactored targets.
- `scripts/check.command` runs the staged strict mypy gate before full mypy and pytest.
