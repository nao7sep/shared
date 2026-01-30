# Poetry Workflow

## What is Poetry?

Poetry is a dependency manager for Python projects. Think of it as:
- **NuGet** (from C#)
- **npm/pnpm** (from JavaScript)
- **Cargo** (from Rust)

**What Poetry does**:
1. Creates and manages virtual environments
2. Tracks dependencies in `pyproject.toml`
3. Locks exact versions in `poetry.lock`
4. Installs dependencies reproducibly
5. Publishes packages (if you're making libraries)

## Installing Poetry

**Recommended: Via Homebrew**:
```bash
brew install poetry
```

**Update Poetry**:
```bash
brew upgrade poetry
```

**Verify installation**:
```bash
which poetry
# Expected: /opt/homebrew/bin/poetry or /usr/local/bin/poetry

poetry --version
```

## Starting a New Project

### Option 1: Create New Project

```bash
cd ~/code
poetry new my-project

# Creates structure:
# my-project/
# ├── pyproject.toml
# ├── README.md
# ├── my_project/
# │   └── __init__.py
# └── tests/
#     └── __init__.py
```

### Option 2: Initialize in Existing Directory

```bash
cd my-existing-project
poetry init
# Interactive prompts:
# - Package name
# - Version
# - Description
# - Author
# - License
# - Dependencies (can skip, add later)

# Creates pyproject.toml
```

## Key Files

### pyproject.toml (You edit this)

Modern Python standard for project configuration:

```toml
[tool.poetry]
name = "my-project"
version = "0.1.0"
description = "My FastAPI project"
authors = ["Your Name <you@example.com>"]
readme = "README.md"

[tool.poetry.dependencies]
python = "^3.11"              # Requires Python 3.11+
fastapi = "^0.109.0"          # Allows 0.109.x, not 0.110.0
uvicorn = {extras = ["standard"], version = "^0.27.0"}
sqlalchemy = "^2.0.0"
pydantic = "^2.5.0"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
black = "^24.1.0"
ruff = "^0.1.0"
httpx = "^0.26.0"             # For testing

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

### poetry.lock (Auto-generated, don't edit)

Locks **exact** versions of all dependencies (including transitive dependencies):

```toml
[[package]]
name = "fastapi"
version = "0.109.2"
description = "FastAPI framework, high performance, easy to learn"
...

[[package]]
name = "pydantic"
version = "2.5.3"          # Exact version locked
...

[[package]]
name = "pydantic-core"     # Transitive dependency
version = "2.14.6"         # Also locked
...
```

**Why it matters**: Ensures everyone on your team gets identical dependency versions.

## Adding Dependencies

### Runtime Dependencies

```bash
# Add a package
poetry add fastapi
# Updates pyproject.toml
# Updates poetry.lock
# Installs to .venv

# Add multiple packages
poetry add fastapi uvicorn sqlalchemy

# Add with extras
poetry add "uvicorn[standard]"
# Installs uvicorn with optional dependencies (watchfiles, websockets)

# Add specific version
poetry add fastapi==0.109.0   # Exact version
poetry add "fastapi>=0.100.0,<0.110.0"  # Range
```

### Development Dependencies

Dependencies needed only for development (testing, linting):

```bash
poetry add --group dev pytest pytest-asyncio httpx black ruff mypy

# Or shorter form
poetry add -G dev pytest black ruff
```

**In pyproject.toml**:
```toml
[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
black = "^24.1.0"
```

**Installing without dev dependencies** (e.g., in production):
```bash
poetry install --without dev
```

## Version Constraints

Poetry uses semantic versioning constraints:

```toml
# Caret (^) - recommended, allows compatible updates
fastapi = "^0.109.0"
# Allows: >=0.109.0, <0.110.0
# Allows: 0.109.1, 0.109.2, etc.
# Blocks: 0.110.0 (breaking changes)

# Tilde (~) - more restrictive
fastapi = "~0.109.0"
# Allows: >=0.109.0, <0.109.1
# Only patch updates

# Wildcard (*)
fastapi = "*"
# Any version (don't use in production)

# Exact
fastapi = "0.109.0"
# Only this exact version

# Multiple constraints
fastapi = ">=0.100.0,<0.110.0"
# Range between 0.100.0 and 0.110.0
```

**Recommendation**: Use `^` for most dependencies. Use exact versions only when needed (e.g., known bugs in newer versions).

## Installing Dependencies

### Fresh Install

```bash
cd my-project

# Install all dependencies from poetry.lock
poetry install
# Creates .venv if not present
# Installs exact versions from poetry.lock
# Includes dev dependencies by default

# Without dev dependencies
poetry install --without dev
```

### Updating Dependencies

```bash
# Update all dependencies (within constraints)
poetry update
# Respects version constraints in pyproject.toml
# Updates poetry.lock with new versions

# Update specific package
poetry update fastapi

# Update and show what changed
poetry update --dry-run
```

**Example**:
- `pyproject.toml` says: `fastapi = "^0.109.0"`
- `poetry.lock` has: `fastapi = "0.109.2"`
- New version available: `0.109.5`
- `poetry update fastapi` updates lock to `0.109.5`
- Won't update to `0.110.0` (outside `^0.109.0` constraint)

## Removing Dependencies

```bash
# Remove a package
poetry remove fastapi
# Updates pyproject.toml
# Updates poetry.lock
# Uninstalls from .venv

# Remove dev dependency
poetry remove --group dev pytest
```

## Running Commands

### Using poetry run

```bash
# Run Python script
poetry run python app/main.py

# Run installed executable
poetry run uvicorn app.main:app --reload

# Run tests
poetry run pytest

# Run formatter
poetry run black .

# Run linter
poetry run ruff check .
```

### Using poetry shell

```bash
# Activate virtual environment in new shell
poetry shell

# Now you can run commands directly
python app/main.py
uvicorn app.main:app --reload
pytest
black .

# Exit shell to deactivate
exit
```

## Viewing Dependencies

```bash
# List all installed packages
poetry show

# Show dependency tree
poetry show --tree
# Example output:
# fastapi 0.109.2
# ├── pydantic >=1.7.4
# │   └── pydantic-core 2.14.6
# ├── starlette 0.36.3
# └── typing-extensions >=4.8.0

# Show specific package details
poetry show fastapi
# Shows: version, description, dependencies, required by

# Show outdated packages
poetry show --outdated
```

## Managing Virtual Environments

```bash
# Show .venv info
poetry env info
# Shows: Python version, .venv path, etc.

# Show .venv path only
poetry env info --path

# List all virtual environments for this project
poetry env list

# Use specific Python version
poetry env use 3.12
poetry env use 3.11

# Remove virtual environment
poetry env remove python
# Deletes .venv (run poetry install to recreate)

# Configure Poetry to create .venv in project directory
poetry config virtualenvs.in-project true
# Future projects will have .venv in project root
```

## Common Workflows

### Starting a New FastAPI Project

```bash
# 1. Create project
mkdir my-api
cd my-api
poetry init
# Answer prompts (or skip dependencies)

# 2. Add dependencies
poetry add fastapi uvicorn sqlalchemy alembic pydantic-settings
poetry add -G dev pytest pytest-asyncio httpx black ruff

# 3. Create app structure
mkdir app
touch app/__init__.py app/main.py

# 4. Run development server
poetry run uvicorn app.main:app --reload
```

### Cloning Existing Project

```bash
# 1. Clone repository
git clone https://github.com/user/project.git
cd project

# 2. Install dependencies from poetry.lock
poetry install
# Creates .venv
# Installs exact versions from lock file

# 3. Run project
poetry run uvicorn app.main:app --reload
```

### Updating Project After Homebrew Python Upgrade

```bash
# Homebrew upgraded Python 3.11 → 3.12

cd my-project

# 1. Remove old .venv
poetry env remove python

# 2. Recreate with new Python
poetry install
# Creates fresh .venv with Python 3.12
# Reinstalls all packages from poetry.lock
```

## Dependency Conflicts

Poetry checks for conflicts when you add packages:

```bash
poetry add package-a package-b
# If package-a requires dependency-x ^2.0
# And package-b requires dependency-x ^3.0
# Poetry shows error:
#
# Because package-a (1.0) depends on dependency-x (^2.0)
# and package-b (1.0) depends on dependency-x (^3.0),
# package-a (1.0) is incompatible with package-b (1.0).
```

**Solutions**:
1. Update one package to a newer version that's compatible
2. Check if newer versions of packages resolve conflict
3. Use different packages if incompatible

## Git Workflow

**Always commit**:
```bash
git add pyproject.toml poetry.lock
git commit -m "Add dependencies"
```

**Never commit**:
```bash
# .gitignore
.venv/
__pycache__/
*.pyc
.pytest_cache/
```

**Why commit poetry.lock**:
- Ensures everyone gets same dependency versions
- Prevents "works on my machine" issues
- Lock file is source of truth for exact versions

## Configuration

**View config**:
```bash
poetry config --list
```

**Useful settings**:
```bash
# Create .venv in project directory (recommended)
poetry config virtualenvs.in-project true

# Disable .venv creation (use manually created venvs)
poetry config virtualenvs.create false
```

## Troubleshooting

### "Command not found" after poetry install

**Problem**: Installed package executable not in PATH

**Solution**: Use `poetry run` or `poetry shell`:
```bash
poetry run uvicorn app.main:app
# Or
poetry shell
uvicorn app.main:app
```

### Dependencies not updating

**Problem**: `poetry update` doesn't get latest version

**Check**:
```bash
# What does pyproject.toml allow?
cat pyproject.toml
# If it says fastapi = "^0.100.0", it won't update to 0.200.0

# Solution: Update constraint
poetry add fastapi@^0.200.0
```

### Slow dependency resolution

**Problem**: `poetry add` takes forever

**Cause**: Complex dependency tree, many packages

**Solution**: Be patient, or use `--dry-run` to preview:
```bash
poetry add fastapi --dry-run
```

## Summary

**Key files**:
- `pyproject.toml` - Dependencies and constraints (you edit)
- `poetry.lock` - Exact versions (auto-generated, commit to git)
- `.venv/` - Virtual environment (don't commit)

**Common commands**:
```bash
poetry init                    # Initialize new project
poetry add <package>           # Add dependency
poetry add -G dev <package>    # Add dev dependency
poetry install                 # Install from poetry.lock
poetry update                  # Update dependencies
poetry run <command>           # Run in .venv context
poetry shell                   # Activate .venv
poetry show                    # List dependencies
poetry env info                # Show .venv info
```

**Workflow**:
1. `poetry init` or `poetry new`
2. `poetry add` dependencies
3. Code your project
4. `poetry run` to execute
5. `git add pyproject.toml poetry.lock` and commit

Next: Learn about async in Python in 04-async-in-python.md
