# Pydeli Specification and Plan

Context: derived from the March 5, 2026 `pydeli` design chat. This document is intentionally standalone and includes the CLI, path, and timestamp conventions it depends on. Packaging and publishing assumptions were rechecked against official `uv`, PyPI, and Python packaging documentation on March 6, 2026.

## Purpose

Build `pydeli`, a wizard-style Python release helper for publishing one app at a time from the monorepo to TestPyPI and then PyPI, while keeping reproducible local archives and guiding first-time setup.

## Scope

- Release exactly one target app per run.
- Support interactive use directly or through per-app `release.command` wrappers.
- Validate local version consistency before any publish.
- Query remote registries as the source of truth for existing versions.
- Build, archive, publish to TestPyPI, verify in isolation, and optionally publish the same build to PyPI.
- Persist only the local state needed for credentials and bootstrap flow outside the repo.
- Document version-stage guidance and first-time publishing steps for the user.

## Console Output Contract

- Prioritize simplicity and maintainability over terminal aesthetics.
- Output is plain text by default. Do not rely on color or text decoration for meaning.
- Every output segment emits exactly one leading empty line except the first segment of the process, which emits none.
- No segment emits a trailing empty line.
- Relevant segment types for `pydeli` are:
  - banner
  - prompt
  - result
  - list
  - summary with list
  - confirmation dialog
  - warning
  - error
  - progress
  - empty-state feedback
  - farewell
- A prompt and its immediate result are one visual unit. Do not place a blank line between them.
- Segments may legitimately appear before the banner, such as config or credential errors detected during startup.
- Multiple warnings or errors from one operation are a single segment. Do not separate them with blank lines.
- If output includes multiple `key: value` lines, pad keys so all values start in the same column.
- Always print explicit empty-state feedback when there is nothing to show.
- Only show a follow-up selection prompt when there is something selectable.
- Do not hard-wrap runtime output to a fixed width. Let the terminal wrap long lines.
- Avoid borders unless they add real value. If a border is used, it must be exactly 80 characters wide.
- If a command can emit output longer than the terminal height, paginate it instead of dumping an unbounded scroll.

## Interactive CLI Rules

- `pydeli` is a one-shot interactive wizard, not a REPL.
- The CLI signature for v1 is `pydeli <app-dir> --archive-dir <archive-dir>`.
- `<app-dir>` is the single required positional argument. `--archive-dir` is a required named option.
- Do not add short flags for workflow behavior. If future boolean flags are added, they are presence-only and never take `=true` or `true/false` values.
- Unrecognized named options must fail immediately with a visible error.
- Help output must remain available even when required arguments are missing.
- It must only enter interactive flow when stdin and stdout are attached to a terminal.
- If launched non-interactively, it must fail fast with a clear user-facing message instead of hanging for input.
- Interactive choices belong inside the wizard. Do not duplicate them as alternate CLI behavior flags.
- Use `Rich` for terminal output.
- Use `Questionary` for confirmations, menus, and masked secret entry.
- Use `prompt_toolkit` for free-text prompt input when a menu or confirmation is not sufficient.
- Define the runnable app name via `[project.scripts]` so the tool is invocable as `pydeli`.
- Use structured prompts for confirmations, selections, and masked secret entry rather than raw unstructured input.
- Secret input must be masked and must never be echoed, logged, or persisted in command history.
- Secondary answers such as `y`, `n`, or menu selections must not pollute any reusable input-history mechanism.
- Expected failures and usage errors are caught at the CLI boundary and shown as clear user-facing error messages.
- `Ctrl+C` must cancel safely without a traceback. During a sub-flow or long-running step, it should abort the current operation, print a clear cancellation message, and return to the nearest safe wizard boundary.

## Path Resolution Rules

- Normalize incoming path text from NFD to NFC before checks and reject any path containing NUL.
- Never resolve paths relative to the current working directory.
- Accept absolute paths as-is.
- Expand `~` to the user home directory.
- Because `pydeli` does not accept an explicit base directory for path resolution, pure relative paths are rejected in v1.
- Reject Windows rooted-but-not-fully-qualified forms such as `\temp` and `C:temp`.
- Accept forward-slash and backslash input styles and preserve Unicode safely.
- Resolve dot segments only after the path has been placed in an explicit absolute context.
- If `pydeli` ever derives a filename from a project or package name, sanitize one filename segment at a time, never a full path.
- Derived filename segments should preserve letters, numbers, `_`, `-`, and `.`, convert other characters to `-`, collapse repeated replacements, trim outer hyphens and periods, and fail if the result becomes empty.

## Timestamp Rules

- Internal timestamps for state, logs, and machine-readable records use high-precision UTC with an explicit UTC marker.
- UTC-valued fields and variables include `utc` in their names.
- User-facing timestamps default to local time and omit timezone suffixes unless disambiguation is needed.
- Logs should default to the same high-precision UTC format used for internal timestamps.
- If `pydeli` creates timestamped filenames in the future, use `YYYY-MM-DD_HH-MM-SS_<semantic-group>.<ext>`.

## Final Decisions

### Interaction Model

- `pydeli` is a one-shot interactive wizard. It must not expose a REPL.
- CLI inputs are limited to:
  - required positional target app path
  - required `--archive-dir` path
- Workflow mode is chosen interactively inside the wizard. Do not implement `--dry-run` or `--wet-run`.
- `.command` wrappers are a first-class launch path.
- If stdin/stdout are not interactive, fail fast with a clear message instead of hanging in a prompt loop.

### Release Workflow

- Each run targets exactly one app.
- Remote registries are the source of truth for version existence. `pydeli` must not keep a local release-history database.
- Normal publish flow:
  1. Resolve and validate paths.
  2. Load local version evidence.
  3. Enforce version consistency.
  4. Query TestPyPI and PyPI for existing versions.
  5. Ensure the local version is publishable.
  6. Ensure required credentials and bootstrap state exist.
  7. Build artifacts.
  8. Archive artifacts locally.
  9. Publish to TestPyPI.
  10. Verify the installed package in an isolated environment.
  11. Ask once whether to publish the exact build to PyPI.
  12. Publish to PyPI if approved.
- A preflight-only path must also exist and be selected interactively. It stops before any publish and may reuse the same archive paths as a later full publish.
- Local archive files for the same version are silently overwritten without confirmation.

### Version Policy

- `pydeli` is read-only with respect to source version files. It never edits `pyproject.toml`, `__init__.py`, `__main__.py`, or other source files.
- `pydeli` must read version values from all supported known locations and require exact equality across them.
- Minimum known locations for v1:
  - `pyproject.toml` `[project].version`
  - `src/<module>/__init__.py` or `<module>/__init__.py`
  - `src/<module>/__main__.py` or `<module>/__main__.py`
- In Python source files, `pydeli` should recognize the standard `__version__ = "..."` or `__version__ = '...'` assignment shape.
- If no supported version source is found, fail loudly.
- Use PEP 440 ordering rules for all comparisons. Do not invent a custom comparison algorithm.
- If the local version already exists on the selected registry path, or is not newer than the highest relevant remote version, halt, show the remote evidence, and instruct the user to update version strings manually before rerunning.
- The README should explain the release-stage order: `dev` -> `a` -> `b` -> `rc` -> final -> `post`.
- `pydeli` may recommend the `__version__` convention and should recognize it when scanning, but it should not assume every future app stores version data in exactly the same files forever.

### Registry And Publishing Policy

- Support both TestPyPI and PyPI.
- Treat TestPyPI as the required staging registry before PyPI for the normal publish flow.
- First-release setup must guide the user through the necessary bootstrap steps with exact URLs and clear browser instructions, then transition to project-scoped credentials for steady-state releases.
- The bootstrap flow must support an account-wide token when a registry requires it for first publication, then rotate to a project-scoped token once project-scoped credentials are available.
- Guided bootstrap steps must pause for user action and resume only after the user supplies the requested result.
- Keep credentials and publication state outside the monorepo.
- Persist credential and bootstrap metadata as JSON under `platformdirs.user_data_dir("Pydeli")`.
- Never pass secrets on the command line. Provide them only at the subprocess environment boundary needed for publication, such as the environment variables consumed by `uv publish`.
- Do not perform git-cleanliness checks.
- Do not rename build artifacts. Archive the exact filenames produced by the build backend.

### Build And Archive Policy

- `pydeli` delegates artifact naming to the target app's build backend via `uv build`.
- `--archive-dir` is an app-specific archive root supplied by the caller.
- Within that root, `pydeli` should store artifacts under a version-specific subdirectory.
- The archive exists for reproducibility and quick local re-installation, not as the canonical version ledger.

### Verification Policy

- After TestPyPI publish, `pydeli` creates an isolated temporary environment, installs the exact uploaded version from TestPyPI, and runs a basic smoke test.
- Verification must use TestPyPI as the primary index and regular PyPI as a fallback index for dependencies.
- The publish-to-PyPI prompt appears only after verification succeeds or after the user explicitly decides how to proceed from a verification failure.

## Implementation Shape

### Core Modules

- `cli.py`: argument parsing, TTY detection, top-level error handling, wizard startup.
- `workflow.py`: stage orchestration and branching between preflight-only and publish flows.
- `models.py`: typed models for release targets, version evidence, registry state, credentials, build artifacts, and run results.
- `paths.py`: shared-spec-compliant path resolution and validation.
- `state_store.py`: local persistent state under `platformdirs.user_data_dir("Pydeli")`.
- `version_audit.py`: source discovery, extraction, equality checks, and normalized version parsing.
- `registry_client.py`: PyPI and TestPyPI JSON API queries and response normalization.
- `builder.py`: `uv build` execution and artifact collection.
- `archive_store.py`: version-subdirectory creation and overwrite behavior.
- `publisher.py`: upload orchestration for TestPyPI and PyPI.
- `verifier.py`: ephemeral-environment install and smoke-test execution.
- `ui.py`: prompt, confirmation, and console-formatting helpers.

### Data Model Expectations

- Use typed models only. No long-lived raw dicts.
- Internal timestamps in state and logs must be stored as UTC and named with `*_utc`.
- Persisted local state is JSON-backed and lives under the app's `platformdirs` data directory.
- Credential metadata should distinguish:
  - registry
  - project or package name
  - token scope intent (`account` vs `project`)
  - created and updated timestamps
  - whether bootstrap rotation is still required
- Release state should be minimal. Persist only what the next run needs.

## Phase Plan

### Phase 1: Project Skeleton And Shared Infrastructure

- Create the app scaffold under `shared/apps/pydeli`.
- Implement the CLI entrypoint, typed models, top-level exception handling, path resolution, and state-directory setup.
- Apply the standalone console-output and interactive-terminal rules from the start.
- Set up the initial `pyproject.toml` entry point and the chosen terminal I/O libraries.

### Phase 2: Version Auditing And Registry Lookups

- Implement version-source discovery and exact-match auditing.
- Add PEP 440 parsing and comparison using standard Python packaging tooling.
- Query both registries each run and surface clear failure messages when the local version is missing, inconsistent, or not newer than the remote state.

### Phase 3: Build And Archive

- Run the target app's build command through `uv`.
- Collect the exact artifacts produced.
- Copy them into `<archive-dir>/<version>/`, silently overwriting matching filenames.

### Phase 4: Token Bootstrap Flow And Publishing

- Implement interactive credential guidance for TestPyPI and PyPI.
- Persist credential state outside the repo via the local state store.
- Publish to TestPyPI first, then pause for the user's confirmation before PyPI.

### Phase 5: Verification Sandbox

- Create the temporary-environment flow.
- Install the exact TestPyPI release with PyPI as dependency fallback.
- Run the configured smoke test and feed the result back into the publish decision.

### Phase 6: Documentation And Wrappers

- Write README guidance covering prerequisites, first-release bootstrap, token rotation, version-stage meanings, and `.command` usage.
- Provide example `release.command` templates for public and private app locations.

### Phase 7: Tests

- Unit tests for path mapping, version extraction, version ordering, and state persistence.
- Integration tests for build/archive behavior, registry decision logic, and publish workflow branching.
- Smoke tests for the verification sandbox, including failure reporting.

## Validated Assumptions

- `uv_build` is a current official `uv` build backend, so `pydeli` should treat the target app's declared backend as authoritative rather than assuming older backend rules.
- Official PyPI docs expose a JSON API for project metadata, which fits the "server is the source of truth" requirement.
- Official PyPI docs support both account-wide and project-scoped API tokens.
- Official Python packaging docs define the version-stage ordering used in the chat.
- The exact bootstrap rule for first project publication still needs to be encoded carefully because official token docs describe scopes but do not fully spell out the first-release workflow.

## Out Of Scope

- Git tagging, commit creation, or git-state enforcement.
- Batch release of multiple apps in one run.
- Automatic editing of version strings in source files.
- A persistent local database of every release ever published.
- Custom build-backend logic for each target app.
- Changelog generation, release-note writing, or CI/CD automation.

## Open Questions

- How should `pydeli` determine the smoke-test command for an arbitrary target app: infer from `[project.scripts]`, default to `--help` or `--version`, or read an explicit per-app config?
- What exact steps belong to the interactive preflight-only path beyond build and archive?
- Should token values themselves live in `pydeli`'s state file, or should `pydeli` store only metadata and delegate secret storage to a more secure mechanism while still meeting the "outside the repo" requirement?
- Should `pydeli` verify the contents of built artifacts for required non-Python resource files, or is that left to the target app's build configuration and external tests?
- What is the minimum supported set of version-source file patterns for v1 beyond `pyproject.toml`, `__init__.py`, and `__main__.py`?

## Immediate Next Step

Use this plan as the handoff document for implementation and resolve the open questions before Phase 4 if they block interface or state-model design.
