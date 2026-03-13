# pydeli

Implementation plan generated from conversation on 2026-03-05, refined on 2026-03-13.

## Overview

pydeli is a Python CLI app that helps publish Python packages to TestPyPI or PyPI. It is an interactive wizard-style tool (not a REPL) designed for a developer who maintains multiple apps in a monorepo and wants a guided, repeatable release workflow without relying on GitHub Actions or Git tags.

The app lives at `~/code/shared/apps/pydeli/`. It uses `uv_build` as its build backend and is invoked via `uv run pydeli`.

### Design Principles

- **Wizard, not REPL.** Publication is a linear, stateful workflow. The app runs once per release action, asks questions as needed, and exits.
- **Read-only regarding source code.** pydeli never modifies the user's source files. It reads version strings for consistency checks only.
- **Single target per run.** Each invocation targets either TestPyPI or PyPI, never both. TestPyPI and PyPI publications are separate runs.
- **CLI args with interactive fallback.** Every parameter can be provided as a CLI option or omitted and answered interactively. This supports both `.command` double-click workflows and direct terminal use.
- **Silent overwrite for archives.** Because registries enforce version immutability, local archives for the same version are always safe to overwrite.

## Requirements

### CLI Interface

- Entry point: `pydeli` (always lowercase), defined in `pyproject.toml` under `[project.scripts]`.
- Invocation: `uv run pydeli [APP_DIR] [--archive-dir DIR] [--target testpypi|pypi] [--dry-run | --wet-run]`.
- All arguments are optional. If omitted, pydeli prompts for each as the workflow requires it.
- `APP_DIR`: path to the app to publish. Accepts absolute paths, `~`-prefixed paths, and `@`-prefixed paths (resolved to pydeli's own app root). Pure relative paths require an explicit base directory context; if ambiguous, reject and ask the user.
- `--archive-dir DIR`: root directory for archived build artifacts. If omitted and not provided interactively, pydeli must ask.
- `--target testpypi|pypi`: which registry to target. If omitted, pydeli asks.
- `--dry-run` / `--wet-run`: mutually exclusive. Dry-run performs all operations except uploading to the registry and test-installing from it. If neither is specified, pydeli asks.
- No other behavior flags. All workflow decisions are handled interactively.

### Configuration

- Config file location: `~/.pydeli/config.json`.
- Auto-created on first run. When pydeli creates the file, it prints a clear message: the file path and its purpose.
- Structure: a JSON object with a `tokens` section containing per-app-per-registry token entries.
- Each app can have up to two token entries: one for TestPyPI and one for PyPI.
- A stored token may be a global (account-wide) token or a project-scoped token. pydeli does not distinguish between them; it stores and uses whatever the user provides.
- Example structure:

```json
{
  "tokens": {
    "my-app": {
      "testpypi": "pypi-...",
      "pypi": "pypi-..."
    }
  }
}
```

### Version Consistency Audit

- pydeli scans the target app directory for version strings in these files:
  1. `pyproject.toml` — parsed with a TOML library, reading `[project].version`.
  2. `<package>/__init__.py` — regex match for `__version__\s*=\s*["']([^"']+)["']`. Searches both `src/<package>/` and `<package>/` layouts.
  3. `<package>/__main__.py` — same regex, same search locations.
- The package name is derived from the `[project].name` field in `pyproject.toml`, with hyphens converted to underscores per Python packaging conventions.
- All discovered version strings must be identical. If any mismatch is found, pydeli halts with a clear error showing every source and its value.
- If only one source is found (typically `pyproject.toml` alone), pydeli emits a warning but continues. This is a consistency check, not a hard gate.
- Version parsing and comparison use `packaging.version.Version` (from the `packaging` library). This handles the full PEP 440 specification without custom parsing logic.

### Version Newness Check

- After confirming local consistency, pydeli queries the targeted registry's JSON API to check whether the local version already exists remotely.
  - PyPI: `https://pypi.org/pypi/<package>/json`
  - TestPyPI: `https://test.pypi.org/pypi/<package>/json`
- If the package does not exist on the registry at all (HTTP 404), this is treated as a first-time publication — the version is considered new.
- If the local version already exists on the target registry, pydeli halts with a message telling the user to bump the version and run again.
- pydeli checks only the targeted registry, not both. TestPyPI and PyPI are independent namespaces with independent version histories.

### Token Management

- When pydeli needs a token for the target registry and no token is stored for the current app + registry combination, it enters a guided setup flow:
  1. Prints the exact URL to visit (e.g., `https://pypi.org/manage/account/token/` or the TestPyPI equivalent).
  2. Explains what scope to select.
  3. Prompts for the token value using masked input (characters not echoed).
  4. Saves the token to `config.json`.
- On every run that uses a token, pydeli prints a reminder: a short message suggesting the user switch from a global token to a project-scoped token if they have not already done so. This message appears unconditionally on every run. It is phrased as advisory (e.g., "If you haven't already, consider switching to a project-scoped token for this app...") and never blocks the workflow.
- When publishing, pydeli injects the token into the subprocess environment via `UV_PUBLISH_TOKEN`. The token is never passed as a CLI argument.

### Build

- pydeli runs `uv build` in the target app's directory.
- The build produces `.whl` and `.tar.gz` files in a `dist/` subdirectory with standard PEP 427/625-compliant filenames.
- pydeli does not rename or modify the build output filenames. `uv build` and the registry enforce naming rules.
- If the build fails, pydeli halts with the error output from `uv build`.

### Archiving

- After a successful build, pydeli copies all files from `dist/` to `<archive-dir>/<app-name>/`.
- The archive directory is flat (no version subdirectories). Files are organized by the version-encoding in their standard filenames.
- If files with the same names already exist (e.g., from a previous dry-run or a TestPyPI run for the same version), they are silently overwritten. This is safe because registries enforce version immutability — duplicate local archives are guaranteed to be from unpublished attempts or a complementary registry run.
- The `<archive-dir>/<app-name>/` directory is created automatically if it does not exist.

### Publication (Wet-Run Only)

- In a wet-run, after build and archive, pydeli uploads the artifacts to the target registry using `uv publish`.
- The registry URL is set explicitly:
  - TestPyPI: `--publish-url https://test.pypi.org/legacy/`
  - PyPI: default (no URL override needed)
- The token is injected via the `UV_PUBLISH_TOKEN` environment variable for the subprocess.
- If publication fails, pydeli prints the error and exits.
- In a dry-run, pydeli stops after build and archive. No upload, no test-install.

### Verification (Wet-Run, Post-Publication, Optional)

- After a successful wet-run upload, pydeli asks the user whether they want to test-install the just-published package. This is optional because many updates are trivial and the user may not need to verify.
- If the user chooses to verify:
  1. pydeli creates a temporary virtual environment using `uv venv` in a system temp directory.
  2. pydeli installs the package from the target registry into the temp venv. When installing from TestPyPI, `--extra-index-url https://pypi.org/simple/` is added so that the app's dependencies (which live on PyPI) can be resolved.
  3. pydeli opens a **separate terminal window** and runs the installed app's CLI entry point there so the user can interact with it freely. The pydeli window remains untouched and safe.
     - **Cross-platform approach (preferred):** Use platform-detection to open a new terminal window. On macOS, this can be done via `open -a Terminal <script>` or AppleScript. On Windows, `start cmd /k <command>`. On Linux, attempt common terminal emulators (`gnome-terminal`, `xterm`, etc.).
     - **If cross-platform support adds unacceptable complexity or dependencies:** implement macOS only and document the limitation clearly. On unsupported platforms, fall back to printing the venv path and activation instructions.
  4. pydeli waits for the user to type `ok` and press Enter. A bare Enter or accidental keypress does not proceed — the exact string `ok` is required to prevent accidental dismissal.
  5. Once the user confirms, pydeli deletes the temporary virtual environment and all its contents.

### Dry-Run vs. Wet-Run

| Step | Dry-Run | Wet-Run |
|---|---|---|
| Version consistency audit | Yes | Yes |
| Version newness check | Yes | Yes |
| Token check | Yes | Yes |
| Build (`uv build`) | Yes | Yes |
| Archive | Yes | Yes |
| Upload to registry | **No** | Yes |
| Test-install verification | **No** | Optional (user is asked) |

Dry-run can be repeated with the same version indefinitely. Once a wet-run succeeds, the version is permanently consumed on the target registry.

## Architecture

### Module Boundaries

- **`cli.py`** — Entry point. Parses CLI arguments. Falls back to interactive prompts for any missing values. Orchestrates the workflow by calling into other modules in sequence. All user-facing I/O (prompts, messages, errors) originates here or is delegated to presentation helpers.
- **`models.py`** — Data models using `dataclass` for simple value objects and Pydantic `BaseModel` where validation or serialization is needed. Key types:
  - `AppInfo`: app name, package name, directory path, discovered version.
  - `BuildArtifact`: file path, artifact type (wheel or sdist).
  - `RegistryTarget`: enum or literal for `testpypi` / `pypi`, with associated URLs.
  - `RunMode`: enum or literal for `dry` / `wet`.
- **`config.py`** — Reads and writes `~/.pydeli/config.json`. Handles auto-creation on first run. Provides typed access to token storage. Never exposes raw dicts beyond this module.
- **`auditor.py`** — Version consistency checker. Scans `pyproject.toml`, `__init__.py`, `__main__.py` for version strings. Returns all discovered versions with their sources. Reports mismatches as structured data; the CLI layer formats the error.
- **`registry.py`** — Communicates with PyPI/TestPyPI JSON APIs. Checks whether a version exists. Returns structured results. Handles HTTP 404 (package not found) as a valid "first-time" signal, not an error.
- **`builder.py`** — Wraps `uv build` execution. Runs the subprocess in the target app's directory. Returns a list of `BuildArtifact` objects pointing to the files in `dist/`.
- **`archiver.py`** — Copies build artifacts to the archive directory. Creates `<archive-dir>/<app-name>/` if needed. Overwrites silently.
- **`publisher.py`** — Wraps `uv publish` execution. Injects the token via environment variable. Sets the publish URL for TestPyPI.
- **`verifier.py`** — Manages the test-install sandbox. Creates temp venv, installs the package, opens a separate terminal window, waits for `ok` confirmation, cleans up.

### Data Flow

```
CLI args / interactive prompts
  |
  v
auditor  -->  version strings from local files
  |
  v
registry -->  version existence check on target
  |
  v
config   -->  token retrieval (or guided setup)
  |
  v
builder  -->  uv build --> BuildArtifact list
  |
  v
archiver -->  copy to archive dir
  |
  v
[wet-run only]
publisher -> uv publish
  |
  v
[wet-run, optional]
verifier --> temp venv, install, test, cleanup
```

### Dependencies

- **Runtime:**
  - `packaging` — PEP 440 version parsing and comparison.
  - `tomli` (or `tomllib` on Python 3.11+) — TOML parsing for `pyproject.toml`.
  - `uv` — used as a subprocess for `build`, `publish`, `venv`, and `pip install`. Not a Python library dependency.
- **No dependency on:** `prompt_toolkit`, `Rich`, `Questionary`, `Typer`. pydeli is a simple wizard; built-in `input()` and `print()` are sufficient. If future complexity warrants it, these can be added, but the initial implementation should stay minimal.
- **Dev:**
  - `pytest` for testing.
  - `ruff` for linting.
  - `mypy` for type checking.

### External Tools (Subprocess)

pydeli invokes these tools as subprocesses. It does not import them as libraries:

| Tool | Purpose | Invocation |
|---|---|---|
| `uv build` | Build wheel and sdist | Run in target app directory |
| `uv publish` | Upload to TestPyPI or PyPI | With `UV_PUBLISH_TOKEN` env var |
| `uv venv` | Create temporary virtual environment | In system temp directory |
| `uv pip install` | Install package into temp venv | With appropriate index URLs |

## Output Formatting

pydeli follows these CLI output conventions:

### Segment Types

Every block of output is one of these types:

| Segment | Usage in pydeli |
|---|---|
| Banner | App name on startup (e.g., `pydeli`). |
| Prompt | Interactive questions (target, dry/wet, app dir, etc.). |
| Result | Outcome of an operation (e.g., "Build succeeded."). |
| Summary with list | Version audit results showing sources and values. |
| Warning | Non-fatal advisories (e.g., only one version source found, token rotation reminder). |
| Error | Fatal failures (e.g., version mismatch, build failure). |
| Progress | Status during build or upload. |
| Empty-state feedback | When there is nothing to report (e.g., no archives found). |
| Farewell | Final message before exit. |

### Spacing Rules

- Every segment emits exactly one leading empty line before its first content line.
- Exception: the very first segment emits no leading empty line.
- No segment emits a trailing empty line.
- A prompt and its immediate result are a tight visual unit with no blank line between them.

### Key-Value Alignment

When displaying multiple key-value pairs (e.g., version audit results), pad all keys to the same width so values start at the same column:

```
pyproject.toml:  1.2.0
__init__.py:     1.2.0
__main__.py:     1.2.0
```

### Text Style

- Plain text only. No colors or decorations by default.
- Structure and readability come from whitespace, indentation, and clear symbols.
- No hard-wrapping of output lines.

## Timestamps

- Internal timestamps (e.g., in `config.json` if ever needed): UTC, ISO 8601 with explicit `Z` marker, high precision. Variable/key names must include `utc`.
- User-facing timestamps: local time, no timezone specifier, human-readable format.
- Filename timestamps (if ever used in archive metadata): `YYYY-MM-DD_HH-MM-SS` pattern with underscores separating semantic groups and hyphens within groups.

## Constants

Named constants are used for:

| Constant | Purpose | Example value |
|---|---|---|
| `TESTPYPI_UPLOAD_URL` | Registry upload endpoint | `https://test.pypi.org/legacy/` |
| `TESTPYPI_API_URL` | Registry JSON API | `https://test.pypi.org/pypi/{package}/json` |
| `PYPI_API_URL` | Registry JSON API | `https://pypi.org/pypi/{package}/json` |
| `TESTPYPI_INDEX_URL` | pip index for test installs | `https://test.pypi.org/simple/` |
| `PYPI_INDEX_URL` | pip extra index for dependency resolution | `https://pypi.org/simple/` |
| `UV_PUBLISH_TOKEN_ENV` | Environment variable name for token injection | `UV_PUBLISH_TOKEN` |
| `CONFIG_DIR` | Config directory path | `~/.pydeli` |
| `CONFIG_FILENAME` | Config file name | `config.json` |
| `VERSION_FILE_CANDIDATES` | Files to scan for `__version__` | `["__init__.py", "__main__.py"]` |
| `VERSION_PATTERN` | Regex for `__version__` extraction | `^__version__\s*=\s*["']([^"']+)["']` |
| `VERIFICATION_CONFIRM_STRING` | Required input to dismiss verification | `ok` |

Inline-acceptable values (not extracted): format strings, log messages, `0`/`1`/`True`/`False`, test expectations.

## Implementation Steps

1. **Project scaffolding.** Create `~/code/shared/apps/pydeli/` with `pyproject.toml` (using `uv_build` backend, `pydeli` entry point under `[project.scripts]`, `packaging` as a dependency), `src/pydeli/__init__.py`, `src/pydeli/__main__.py`. Confirm `uv run pydeli` launches.

2. **Data models.** Define `AppInfo`, `BuildArtifact`, `RegistryTarget`, `RunMode` in `models.py`.

3. **Config module.** Implement `config.py`: read/write `~/.pydeli/config.json`, auto-create with empty structure on first access, token get/set by app name and registry target.

4. **Version auditor.** Implement `auditor.py`: scan `pyproject.toml` (TOML parser) and `__init__.py`/`__main__.py` (regex) in the target app directory. Return all discovered version strings with source labels. Detect `src/` layout vs flat layout.

5. **Registry client.** Implement `registry.py`: query PyPI/TestPyPI JSON API for a package. Return whether a specific version exists. Handle 404 as "package not yet published."

6. **Builder.** Implement `builder.py`: run `uv build` in the target app directory as a subprocess. Parse `dist/` contents into `BuildArtifact` list.

7. **Archiver.** Implement `archiver.py`: copy build artifacts to `<archive-dir>/<app-name>/`. Create directory if needed. Overwrite silently.

8. **Publisher.** Implement `publisher.py`: run `uv publish` with token injected via `UV_PUBLISH_TOKEN` env var. Set `--publish-url` for TestPyPI.

9. **Verifier.** Implement `verifier.py`: create temp venv with `uv venv`, install package with `uv pip install` (with appropriate index URLs), open app in a separate terminal window (cross-platform with macOS priority), wait for `ok` input, delete temp venv on completion.

10. **CLI orchestrator.** Implement `cli.py`: parse optional CLI args, prompt for missing values, execute the workflow steps in order. Handle errors at the top level with clear user-facing messages. Wire up all modules.

11. **Token guidance flow.** Integrate guided token setup into the CLI: detect missing tokens, print step-by-step instructions with exact URLs, accept masked input, save to config. Add the per-run advisory message about switching to project-scoped tokens.

12. **Testing.** Write tests for the auditor (version extraction, mismatch detection, single-source warning), registry client (version exists, 404 handling), config module (auto-creation, token CRUD), and archiver (directory creation, overwrite behavior). Builder, publisher, and verifier tests can mock subprocess calls.

## PEP 440 Version Reference

For the developer's convenience, pydeli's README should include this lifecycle progression:

1. `X.Y.Z.devN` — Development: not feature-complete, scratchpad testing.
2. `X.Y.ZaN` — Alpha: feature-complete but unstable, requires focused testing.
3. `X.Y.ZbN` — Beta: mostly stable, standard bugs expected.
4. `X.Y.ZrcN` — Release Candidate: believed bug-free, final validation.
5. `X.Y.Z` — Final: production-ready.
6. `X.Y.Z.postN` — Post-release: metadata or documentation corrections without code changes.

## `.command` File Usage

pydeli is designed for double-click execution via macOS `.command` files. Example:

```bash
#!/usr/bin/env bash
# ~/code/shared/apps/my-app/release.command
uv run --directory ~/code/shared/apps/pydeli pydeli \
  --archive-dir ~/code/shared/releases
```

This specifies only the archive directory. pydeli will interactively ask for the target app directory, registry target, and dry/wet mode. More arguments can be added to the `.command` file to skip additional prompts.

## Open Questions

- **Cross-platform terminal window:** The exact mechanism for opening a separate terminal window on Linux and Windows needs investigation during implementation. If it requires external dependencies or significant complexity, macOS-only support is acceptable with clear documentation.
- **Package name derivation:** When the `[project].name` in `pyproject.toml` contains hyphens, the import package name uses underscores (e.g., `my-app` becomes `my_app`). The auditor must handle this mapping. Whether to also support a `[tool.pydeli].package` override in `pyproject.toml` for unusual layouts is undecided.
- **TestPyPI dependency resolution:** When test-installing from TestPyPI, the app's dependencies must come from regular PyPI via `--extra-index-url`. If a dependency has the same name on TestPyPI and PyPI, the wrong version could be pulled. This is a known limitation of TestPyPI and not something pydeli can fully solve.
- **Async considerations:** All subprocess calls (`uv build`, `uv publish`, etc.) are synchronous. If any operation is slow enough to warrant progress indicators or cancellation, async execution may be considered later.
