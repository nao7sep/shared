# Virtual Environments

## The Problem Without Virtual Environments

Imagine you have:
- **Project A**: Requires FastAPI 0.100.0
- **Project B**: Requires FastAPI 0.109.0

If you install both to Homebrew Python's pip, they conflict. Only one version can exist.

**Virtual environments solve this**: Each project gets its own isolated Python environment.

## What is .venv?

`.venv` (or `venv`) is a directory in your project that contains:

1. **Symlinks to Homebrew Python** interpreter
2. **Copies of pip packages** (actual files, not symlinks)
3. **Isolated site-packages** directory

**Visual structure**:
```
my-project/
├── .venv/                    # Virtual environment
│   ├── bin/
│   │   ├── python3 -> /opt/homebrew/bin/python3  # Symlink
│   │   ├── pip3                                   # Installed here
│   │   └── uvicorn                                # Installed here
│   ├── lib/
│   │   └── python3.12/
│   │       └── site-packages/  # All packages go here
│   │           ├── fastapi/    # Actual files
│   │           ├── pydantic/   # Actual files
│   │           └── ...
│   └── pyvenv.cfg
├── app/                      # Your code
└── pyproject.toml            # Dependencies list
```

## Creating Virtual Environments (Manual)

You typically won't do this manually (Poetry does it for you), but it's good to understand:

```bash
cd my-project

# Create virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate

# Your prompt changes to show (.venv)
# Now pip installs go into .venv, not Homebrew Python
pip install fastapi

# Deactivate
deactivate
```

## Creating Virtual Environments (Poetry)

**Poetry automates this**:

```bash
cd my-project

# Initialize project
poetry init

# Add a dependency - creates .venv if not present
poetry add fastapi
# Poetry creates .venv automatically
# Poetry installs fastapi to .venv/lib/python3.x/site-packages/

# Run commands in the virtual environment
poetry run uvicorn app.main:app --reload

# Or spawn a shell with .venv activated
poetry shell
```

## What's Inside .venv

### 1. Python Interpreter (Symlink)

```bash
ls -l .venv/bin/python3
# Shows symlink to Homebrew Python
# .venv/bin/python3 -> /opt/homebrew/bin/python3
```

**Why symlink?**
- Saves disk space (no duplicate Python interpreter)
- Automatically uses current Homebrew Python version

**Consequence**: When Homebrew Python updates, this symlink may break.

### 2. Pip Packages (Actual Files)

```bash
ls .venv/lib/python3.12/site-packages/
# Shows actual directories:
# fastapi/
# pydantic/
# sqlalchemy/
# etc.
```

These are **copies** (or newly downloaded), not symlinks. Each project has its own.

### 3. Scripts/Executables

```bash
ls .venv/bin/
# Shows:
# python3 (symlink)
# pip3 (installed)
# uvicorn (installed with uvicorn package)
# pytest (if installed)
```

When you run `poetry run uvicorn`, it uses `.venv/bin/uvicorn`.

## Why Isolation Matters

**Without .venv**:
```bash
python3 -m pip install fastapi==0.100.0  # Installs to Homebrew Python
cd ../other-project
python3 -m pip install fastapi==0.109.0  # Overwrites 0.100.0!
# First project now broken
```

**With .venv**:
```bash
cd project-a
poetry add fastapi==0.100.0  # Installs to project-a/.venv
cd ../project-b
poetry add fastapi==0.109.0  # Installs to project-b/.venv
# Both projects work independently
```

## When Homebrew Python Updates

**Scenario**: Homebrew upgrades Python 3.11 → 3.12

**What happens**:
- Homebrew Python symlink changes: `python3 -> .../python3.12` (was python3.11)
- Your `.venv/bin/python3` symlink may break (points to old 3.11)

**Fix**:
```bash
cd your-project

# Remove old .venv
poetry env remove python

# Recreate with new Python version
poetry install
# Creates fresh .venv with Python 3.12
# Reinstalls all packages from poetry.lock
```

**When to do this**:
- After Homebrew Python major/minor version update
- If you see errors about "Python not found" when running poetry

## .gitignore and .venv

**ALWAYS ignore .venv in git**:

```bash
# .gitignore
.venv/
__pycache__/
*.pyc
```

**Why**:
- Large (hundreds of MB)
- Machine-specific (contains symlinks)
- Recreatable from `poetry.lock`

**What to commit**:
```bash
git add pyproject.toml poetry.lock
git commit -m "Add project dependencies"
```

## Multiple Virtual Environments

You can have different Python versions per project:

```bash
# Project A uses Python 3.11
cd project-a
poetry env use 3.11
poetry install

# Project B uses Python 3.12
cd project-b
poetry env use 3.12
poetry install
```

**Requirement**: Both Python versions must be installed via Homebrew:
```bash
brew install python@3.11 python@3.12
```

## Locating Your .venv

**With Poetry**:
```bash
# Show .venv location
poetry env info --path
# Example output: /Users/nao7sep/code/my-project/.venv

# List all Poetry environments
poetry env list
```

**Default location**:
- Poetry creates `.venv` in project root (if configured)
- Or in a central cache directory (depends on Poetry config)

**Configure Poetry to use project-local .venv**:
```bash
poetry config virtualenvs.in-project true
# Future projects will have .venv in project root
```

## Activating vs Running

**Two ways to use .venv**:

### Option 1: Activate
```bash
poetry shell
# Spawns new shell with .venv activated
# Prompt shows: (.venv)

python3 --version  # Uses .venv Python
pip list           # Shows .venv packages
uvicorn app.main:app --reload  # Runs from .venv

exit  # Deactivate
```

### Option 2: Run (without activating)
```bash
poetry run python3 --version
poetry run uvicorn app.main:app --reload
poetry run pytest
# Executes in .venv without activating shell
```

**Preference**: Use `poetry run` for single commands, `poetry shell` for interactive work.

## Summary

**Virtual environment = project sandbox**:
- Contains symlink to Homebrew Python interpreter
- Contains actual copies of pip packages
- Isolated from other projects

**How Poetry uses .venv**:
- Creates automatically when you add first dependency
- Installs packages to `.venv/lib/python3.x/site-packages/`
- Uses `poetry.lock` to ensure reproducible environments

**Key commands**:
```bash
poetry add <package>           # Installs to .venv
poetry run <command>           # Runs in .venv context
poetry shell                   # Activates .venv
poetry env info --path         # Show .venv location
poetry env remove python       # Delete .venv (to rebuild)
```

**Golden rule**: Never commit `.venv` to git. Always commit `pyproject.toml` and `poetry.lock`.

Next: Learn Poetry workflow in 03-poetry-workflow.md
