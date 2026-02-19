# uv Workflow

## What is uv?

uv is an all-in-one Python toolchain. Think of it as:
- **NuGet** (from C#)
- **npm/pnpm** (from JavaScript)
- **Cargo** (from Rust)

**What uv does**:
1. Installs and manages Python versions
2. Creates and manages virtual environments
3. Tracks dependencies in `pyproject.toml`
4. Locks exact versions in `uv.lock`
5. Installs dependencies reproducibly
6. Builds and publishes packages

## Installing uv

**Recommended: Via Homebrew**:
```bash
brew install uv
```

**Update uv**:
```bash
brew upgrade uv
```

**Verify installation**:
```bash
which uv
# Expected: /opt/homebrew/bin/uv or /usr/local/bin/uv

uv --version
```

## Starting a New Project

### Option 1: Create New Project

```bash
cd ~/code
uv init my-project

# Creates structure:
# my-project/
# ├── pyproject.toml
# ├── README.md
# ├── src/
# │   └── my_project/
# │       └── __init__.py
# └── .python-version
```

### Option 2: Initialize in Existing Directory

```bash
cd my-existing-project
uv init
# Creates pyproject.toml
```

## Key Files

### pyproject.toml (You edit this)

Modern Python standard for project configuration:

```toml
[build-system]
requires = ["uv_build"]
build-backend = "uv_build"

[project]
name = "my-project"
version = "0.1.0"
requires-python = ">=3.9"
description = "My project"
readme = "README.md"
dependencies = [
    "fastapi",
    "uvicorn",
    "sqlalchemy",
    "pydantic",
]

[project.scripts]
my-app = "my_project.cli:main"

[dependency-groups]
dev = ["pytest", "ruff", "mypy", "httpx"]
```

### uv.lock (Auto-generated, don't edit)

Locks **exact** versions of all dependencies (including transitive dependencies). Ensures everyone gets identical dependency versions.

**Always commit to git.**

## Adding Dependencies

### Runtime Dependencies

```bash
# Add a package
uv add fastapi
# Updates pyproject.toml
# Updates uv.lock
# Installs to .venv

# Add multiple packages
uv add fastapi uvicorn sqlalchemy

# Add with extras
uv add "uvicorn[standard]"
```

### Development Dependencies

Dependencies needed only for development (testing, linting):

```bash
uv add --group dev pytest ruff mypy
```

**In pyproject.toml**:
```toml
[dependency-groups]
dev = ["pytest", "ruff", "mypy"]
```

**Installing without dev dependencies** (e.g., in production):
```bash
uv sync --no-group dev
```

## Installing Dependencies

### Fresh Install

```bash
cd my-project

# Install all dependencies from uv.lock
uv sync
# Creates .venv if not present
# Installs exact versions from uv.lock
# Includes dev dependencies by default

# Without dev dependencies
uv sync --no-group dev
```

### Updating Dependencies

```bash
# Update all dependencies to latest compatible versions
uv lock --upgrade
uv sync

# Update specific package
uv lock --upgrade-package fastapi
uv sync
```

## Removing Dependencies

```bash
# Remove a package
uv remove fastapi
# Updates pyproject.toml
# Updates uv.lock
# Uninstalls from .venv
```

## Running Commands

### Using uv run

```bash
# Run Python script
uv run python app/main.py

# Run installed executable
uv run uvicorn app.main:app --reload

# Run tests
uv run pytest

# Run linter
uv run ruff check .

# Run type checker
uv run mypy src/
```

## Viewing Dependencies

```bash
# Show dependency tree
uv tree

# List installed packages
uv pip list
```

## Managing Virtual Environments

uv creates `.venv` automatically when you run `uv sync`. The `.venv` is always in the project directory.

```bash
# Recreate .venv from scratch
rm -rf .venv
uv sync
```

## Common Workflows

### Starting a New Project

```bash
# 1. Create project
mkdir my-api
cd my-api
uv init

# 2. Add dependencies
uv add fastapi uvicorn sqlalchemy alembic pydantic-settings
uv add --group dev pytest pytest-asyncio httpx ruff mypy

# 3. Create app structure
mkdir -p src/my_api
touch src/my_api/__init__.py src/my_api/main.py

# 4. Run development server
uv run uvicorn my_api.main:app --reload
```

### Cloning Existing Project

```bash
# 1. Clone repository
git clone https://github.com/user/project.git
cd project

# 2. Install dependencies from uv.lock
uv sync
# Creates .venv
# Installs exact versions from lock file

# 3. Run project
uv run uvicorn app.main:app --reload
```

## Git Workflow

**Always commit**:
```bash
git add pyproject.toml uv.lock
git commit -m "Add dependencies"
```

**Never commit**:
```gitignore
.venv/
__pycache__/
*.pyc
.pytest_cache/
```

**Why commit uv.lock**:
- Ensures everyone gets same dependency versions
- Prevents "works on my machine" issues
- Lock file is source of truth for exact versions

## Summary

**Key files**:
- `pyproject.toml` - Dependencies and constraints (you edit)
- `uv.lock` - Exact versions (auto-generated, commit to git)
- `.venv/` - Virtual environment (don't commit)

**Common commands**:
```bash
uv init                        # Initialize new project
uv add <package>               # Add dependency
uv add --group dev <package>   # Add dev dependency
uv sync                        # Install from uv.lock
uv lock --upgrade              # Update all deps
uv run <command>               # Run in .venv context
uv tree                        # Show dependency tree
```

**Workflow**:
1. `uv init`
2. `uv add` dependencies
3. Code your project
4. `uv run` to execute
5. `git add pyproject.toml uv.lock` and commit

Next: 04-async-in-python.md
