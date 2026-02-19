# Python on macOS

## The Three Python Installations

macOS can have multiple Python installations. Understanding which is which prevents breaking your system.

### 1. System Python

**Location**: `/usr/bin/python3`

**Owner**: macOS system

**Purpose**: Used by macOS for system operations

**Rule**: **NEVER touch this**. Don't update it, don't install packages to it, don't use it for development.

**Why**: Updating or modifying system Python can break macOS system tools.

### 2. Homebrew Python

**Location**:
- Apple Silicon: `/opt/homebrew/bin/python3`
- Intel Mac: `/usr/local/bin/python3`

**Owner**: You (managed via Homebrew)

**Purpose**: Your development Python

**Rule**: Use this for all development work. Update it via Homebrew.

**Verification**:
```bash
which python3
# Should show /opt/homebrew/bin/python3 (Apple Silicon)
# or /usr/local/bin/python3 (Intel)

python3 --version
# Shows Homebrew Python version
```

### 3. Project Virtual Environments

**Location**: `your-project/.venv/`

**Owner**: You (created per project)

**Purpose**: Isolated environment for each project's dependencies

**Rule**: Each project gets its own. Created from Homebrew Python.

## Installing Homebrew Python

```bash
# Install Python via Homebrew
brew install python

# Verify installation
which python3
python3 --version
```

## Updating Homebrew Python

```bash
# Update Homebrew itself first
brew update

# Update Python
brew upgrade python

# Verify new version
python3 --version
```

**Important**: When Homebrew Python updates (e.g., 3.11 → 3.12), you'll need to rebuild project virtual environments (covered in document 02).

## Installing Python Tools Globally

Modern Homebrew Python blocks direct `pip install` (PEP 668 "externally managed environment"). Use `uv tool` instead:

```bash
# Install uv (manages everything else)
brew install uv

# Install CLI tools globally via uv tool
uv tool install my-tool
```

**What NOT to install globally**:
Project-specific packages (FastAPI, SQLAlchemy, etc.) — these go in project virtual environments managed by uv.

## Python Symlinks on macOS

Homebrew Python uses symlinks for version management:

```bash
# Check the symlink
ls -l /opt/homebrew/bin/python3
# Shows: python3 -> ../Cellar/python@3.12/3.12.1/bin/python3.12

# When you upgrade Python, Homebrew updates this symlink
# Old: python3 -> ../Cellar/python@3.11/3.11.7/bin/python3.11
# New: python3 -> ../Cellar/python@3.12/3.12.1/bin/python3.12
```

**Benefit**: You don't need to specify version numbers in paths (unlike Windows).

**Consequence**: Your virtual environments contain symlinks to Homebrew Python. When Homebrew Python updates, these symlinks may break (fixed by rebuilding .venv).

## Verification Checklist

Run these commands to verify your setup:

```bash
# 1. Check which Python is active
which python3
# Expected: /opt/homebrew/bin/python3 or /usr/local/bin/python3

# 2. Verify it's from Homebrew
python3 -c "import sys; print(sys.prefix)"
# Expected: /opt/homebrew/... or /usr/local/...

# 3. Verify uv is installed
uv --version
```

## Summary

**Three Pythons**:
- System Python → Don't touch
- Homebrew Python → Use for development, update via `brew upgrade python`
- Project .venv → Created from Homebrew Python, per-project isolation

**Key commands**:
```bash
brew install python        # Install
brew upgrade python        # Update
brew install uv            # Install uv (replaces pip, pipx, pyenv, poetry)
```

Next: Learn about virtual environments in 02-virtual-environments.md
