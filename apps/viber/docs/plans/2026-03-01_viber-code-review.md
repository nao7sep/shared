# Viber Code Review

## Output Directory Inventory

- `docs/plans/`
- `docs/plans/2026-02-26_viber-design-and-implementation-plan.md`
- `docs/plans/2026-02-26_viber-detailed-implementation-plan.md`
- `docs/plans/2026-03-01_viber-code-review.md`

## Findings

### 1. `@` paths resolve under `src/viber`, not the app root

Files:

- `src/viber/cli.py:107`
- `src/viber/path_mapping.py:22`
- `README.md:123`

Evidence:

- `README.md` documents `@/data.json` as app-root-relative path syntax.
- `map_path()` correctly treats `@` as relative to the `app_root_abs` argument.
- `cli._resolve_path()` passes `Path(__file__).resolve().parent`, which is the package directory (`.../src/viber`), not the application root (`.../apps/viber`).

Impact:

- `--data @/data.json` and `--check @/check.html` resolve into the source tree instead of the app root promised by the CLI help and README.
- This can create or overwrite runtime files inside `src/viber/`, which is surprising and easy to miss in version control.

Recommended fix:

- Pass the actual app root from `cli.py`, for example `Path(__file__).resolve().parents[2]`.
- Add a CLI test that asserts the concrete `app_root_abs` value used for `@` paths, not just that `map_path()` was called.

### 2. Group names are not validated against the HTML filename mapping

Files:

- `src/viber/service.py:30`
- `src/viber/renderer.py:40`
- `src/viber/path_mapping.py:66`

Evidence:

- Group creation and rename only enforce case-insensitive raw-name uniqueness.
- HTML output filenames are derived from `slugify(group.name)`.
- `slugify()` can collapse distinct names to the same slug (`"Backend Team"` and `"Backend-Team"` both become `backend-team`).
- `slugify()` can also raise when the sanitized result is empty, but group creation currently allows names like `"!!!"`.

Impact:

- Two distinct groups can overwrite the same check page, and deleting one of them can remove the surviving group's page.
- In `--check` mode, a newly created or renamed group with an empty slug can be saved successfully and then break HTML regeneration immediately afterward.

Recommended fix:

- Validate group names against the renderer's filename contract during create/rename.
- Either enforce slug uniqueness up front, or change `check_page_path()` to include a stable unique component such as `g{group.id}` in the filename.
- Add renderer/service tests for slug collisions and empty-slug names.

### 3. Startup save failures after orphan pruning are uncaught

Files:

- `src/viber/cli.py:89`
- `src/viber/store.py:20`

Evidence:

- `main()` catches load failures and initial HTML render failures, but the `save_database()` call after `prune_orphan_tasks()` is outside any error handling.
- `save_database()` performs filesystem writes directly and can raise `OSError` or `PermissionError`.

Impact:

- If startup needs to prune orphan tasks and the data file cannot be written, the app can terminate with a traceback instead of the clear CLI error handling used elsewhere.
- This violates the stated error-handling rule of catching exceptions at the system boundary and surfacing a user-facing message.

Recommended fix:

- Wrap the post-prune `save_database()` call in a boundary-level `try`/`except` that prints a clear error and exits with status 1.
- Add a startup test that simulates `save_database()` failing after pruning.
