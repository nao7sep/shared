# Update Dependencies

Update the current project's dependencies to their latest compatible versions and verify nothing breaks.

## Detect Project Type

Before starting, identify the project's package manager and ecosystem:

| Indicator | Ecosystem | Tool |
|---|---|---|
| `pyproject.toml` + `uv.lock` | Python | `uv` |
| `pyproject.toml` (no uv.lock) | Python | `uv` (initialize lock) |
| `package.json` + `pnpm-lock.yaml` | Node.js | `pnpm` |
| `package.json` + `package-lock.json` | Node.js | `npm` |
| `package.json` + `yarn.lock` | Node.js | `yarn` |
| `*.csproj` / `*.sln` | C# / .NET | `dotnet` |

If multiple ecosystems are present, update each independently.

## Process

### Python (uv)

1. Run `uv lock --upgrade` then `uv sync` to resolve and install latest versions.
2. Check if any packages now require a newer Python version than specified. If so, find the **oldest** Python that satisfies all requirements and update `pyproject.toml` (and `.python-version` if present).
3. Run the test suite (`uv run pytest` or equivalent).
4. If version conflicts arise: remove upper-bound pins, let uv resolve freely, check what was installed, then re-pin from resolved versions.

### Node.js (npm/yarn/pnpm)

1. Run the appropriate update command (`npm update`, `yarn upgrade`, `pnpm update`).
2. For major version bumps, check changelogs for breaking changes before upgrading.
3. Run the test suite (`npm test` or equivalent).

### C# / .NET (dotnet)

1. Run `dotnet list package --outdated` to identify available updates.
2. Update packages with `dotnet add package <name>` (which installs the latest stable by default) or edit version attributes in `.csproj` and run `dotnet restore`.
3. For major version bumps, check release notes for breaking changes before upgrading.
4. Run the test suite (`dotnet test`).

## Principles

- **Packages as new as possible**: maximize security patches and features.
- **Language runtime as old as possible**: maximize compatibility for users who can't upgrade immediately.
- **If tests fail**: determine whether the failure is caused by the update. Report clearly before attempting any fix.

## Output

Report what was updated, what version changes occurred, and whether tests pass. If anything broke, explain the cause and whether it's fixable or requires pinning to an older version.
