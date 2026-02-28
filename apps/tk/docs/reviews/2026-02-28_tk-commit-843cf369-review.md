# Review: tk changes in commit `843cf369b646ef3f77aac1683dd60cdb83d46359`

## Scope

- Repo: `shared`
- App: `apps/tk`
- Commit reviewed: `843cf369b646ef3f77aac1683dd60cdb83d46359`
- Reviewed files: `apps/tk/src/tk/*.py` and the accompanying `apps/tk/tests/*.py` changes

## Verdict

I found 1 non-minor regression.

The internal CLI path still works and the `tk` test suite passes, but this commit breaks the previously supported Python-facing `tk` API for any out-of-tree callers that still pass or consume dict-shaped objects.

## Findings

### [P2] The refactor removes the existing dict-compatible API surface without a compatibility layer

Affected files:

- `apps/tk/src/tk/data.py`
- `apps/tk/src/tk/models.py`
- `apps/tk/src/tk/profile.py`
- `apps/tk/src/tk/session.py`

Why this is a regression:

- `apps/tk/src/tk/data.py` still describes itself as the "primary import surface" for task data operations, but its helpers now only accept `TaskStore` instances. The wrappers at `apps/tk/src/tk/data.py:12-29` no longer coerce or tolerate dict payloads.
- The commit also removes the dict-like shims from the core models and payload DTOs in `apps/tk/src/tk/models.py`. `Task`, `TaskStore`, `Profile`, `PendingListPayload`, `HistoryFilters`, and `HistoryListPayload` are no longer subscriptable or `.get()`-compatible.
- `apps/tk/src/tk/profile.py:223-315` now returns `Profile` objects from `load_profile()` and `create_profile()`, and `apps/tk/src/tk/session.py:12-27` no longer auto-converts dicts stored in `Session.profile` / `Session.tasks`.

Why this matters:

- Before this commit, the Python API explicitly preserved dict compatibility for existing call sites. This commit removes that behavior without a deprecation path, version bump, or fallback coercion at the exported boundaries.
- `tk` is an installable package (`apps/tk/pyproject.toml`), so this is not just a private refactor. Any automation or integration importing `tk.data`, `tk.profile`, or the DTOs will now fail at runtime even though the CLI still passes its tests.

Concrete repros against the post-commit tree:

- `from tk import data; data.add_task({"tasks": []}, "demo")`
  - Result: `AttributeError: 'dict' object has no attribute 'add_task'`
- `from tk import data; data.save_tasks(path, {"tasks": []})`
  - Result: `AttributeError: 'dict' object has no attribute 'to_dict'`
- `profile = Profile.from_dict(...); profile["timezone"]`
  - Result: `TypeError: 'Profile' object is not subscriptable`

Why the current tests did not catch it:

- The commit rewrites fixtures and assertions to use typed models everywhere.
- It also removes the compatibility-focused tests from `apps/tk/tests/test_models.py`, so the suite now validates only the new internal shape.
- I ran `.venv/bin/pytest -q` in `apps/tk`; all 206 tests passed, which confirms this is an API-compatibility regression rather than an internal logic failure.

Recommended fix:

- Keep the dict-compatible wrappers/shims for one release while the rest of the app uses typed models internally.
- If the breaking change is intentional, make it explicit: bump the package version accordingly and document the migration in README/changelog instead of silently narrowing the runtime contract.
- The lowest-risk option is to preserve coercion at the exported boundaries (`data.py`, `profile.py`, `Session.require_*`) and keep the internal implementation fully typed.

## Validation Notes

- Read `/Users/nao7sep/code/shared/PLAYBOOK.md`
- Followed `/Users/nao7sep/code/shared/prompts/recipes/review-code.md`
- Reviewed the `apps/tk` patch and surrounding source
- Ran `apps/tk` tests: `.venv/bin/pytest -q` -> `206 passed`
- Ran direct Python repro snippets against the post-commit code to confirm the compatibility failures above
