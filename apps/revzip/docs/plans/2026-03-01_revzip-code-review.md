# Revzip Code Review Plan

Date: 2026-03-01

## Findings

### 1. Restore is destructive before extraction succeeds

Files:
- `/Users/nao7sep/code/shared/apps/revzip/src/revzip/extract_service.py`
- `/Users/nao7sep/code/shared/apps/revzip/src/revzip/fs_gateway.py`
- `/Users/nao7sep/code/shared/apps/revzip/src/revzip/zip_gateway.py`

Current behavior:
- `restore_snapshot()` verifies zip integrity, deletes the existing source contents, and then extracts directly back into the source directory.
- If extraction fails after the delete step, the original source tree is already gone.

Concrete evidence:
- A structurally valid zip containing both `dir` and `dir/file.txt` passes `verify_zip_integrity()`.
- During extraction, `zipfile.extractall()` creates `dir` as a file and then fails on `dir/file.txt`.
- After that failure, the source directory no longer contains the user's original files; it contains only the partial extraction output.

Why this matters:
- This is data loss on a normal error path such as malformed-but-readable zip contents, disk-full conditions, or mid-extraction I/O failures.
- It violates the documented restore guarantee that the source should be replaced with the selected snapshot exactly.

Plan:
- Restore into a staging directory first.
- Only swap the staged tree into place after extraction completes successfully.
- Keep the current source tree untouched if verification or extraction fails.
- Add a regression test that reproduces the `dir` plus `dir/file.txt` conflict case.

### 2. Snapshot discovery ignores the metadata's declared zip file

Files:
- `/Users/nao7sep/code/shared/apps/revzip/src/revzip/snapshot_catalog_service.py`
- `/Users/nao7sep/code/shared/apps/revzip/src/revzip/metadata_gateway.py`

Current behavior:
- Metadata parsing requires a `zip_filename` field.
- `discover_snapshots()` ignores that field and always pairs `foo.json` with `foo.zip`.

Concrete evidence:
- A metadata file `a.json` with `zip_filename` set to `b.zip` is accepted without warning when both `a.zip` and `b.zip` exist.
- The resulting `SnapshotRecord` points to `a.zip` while still exposing metadata that claims the archive is `b.zip`.

Why this matters:
- The snapshot list can present comment/timestamp/details from one metadata file while restore uses a different archive file.
- This creates silent metadata/archive drift instead of warning and skipping the bad snapshot.

Plan:
- Decide on a single source of truth for the archive pairing.
- Either require `zip_filename` to match `metadata_path.with_suffix(".zip").name`, or resolve the archive path from `zip_filename` after validating it stays inside `--dest`.
- Warn and skip mismatched metadata instead of restoring ambiguous snapshots.
- Add a regression test for the mismatched `zip_filename` case.

### 3. Unknown `~user` paths crash outside revzip's error boundary

Files:
- `/Users/nao7sep/code/shared/apps/revzip/src/revzip/path_mapping.py`
- `/Users/nao7sep/code/shared/apps/revzip/src/revzip/cli.py`

Current behavior:
- `_map_special_prefixes()` calls `Path(path_text).expanduser()` directly for any path beginning with `~`.
- On a path such as `~definitely-no-such-user-12345/tmp`, `expanduser()` raises `RuntimeError`.
- `main()` only catches `RevzipError`, so that startup failure escapes as a raw traceback.

Why this matters:
- This breaks the app's boundary-level error handling contract.
- A user typo in a mapped path should produce a normal `ERROR:` message, not an uncaught exception.

Plan:
- Catch `RuntimeError` from `expanduser()` and convert it into `PathMappingError` with the argument name included.
- Add a regression test for an unknown-user `~name/...` path.
