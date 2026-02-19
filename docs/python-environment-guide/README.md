# Python Environment Guide

Guide for managing Python installations, virtual environments, and dependencies on macOS.

## Reading Order

1. **01-python-on-macos.md** - Understanding Python installations on macOS
2. **02-virtual-environments.md** - Project isolation with virtual environments
3. **03-uv-workflow.md** - Managing dependencies with uv
4. **04-async-in-python.md** - Async vs sync in Python
5. **05-fastapi-dependencies.md** - Essential packages for FastAPI/GUI development

## Usage

**First-time readers**: Read in order (01 → 05) for complete understanding.

**Returning readers**: Jump to specific documents as needed:
- Confused about which Python to use? → 01-python-on-macos.md
- Need to understand .venv? → 02-virtual-environments.md
- Setting up a new project? → 03-uv-workflow.md
- Choosing between libraries? → 04-async-in-python.md, 05-fastapi-dependencies.md

## Context

These documents assume:
- Using macOS (Apple Silicon or Intel)
- Have Homebrew installed
- New to Python, coming from C# background
- Want to avoid breaking system Python

## Key Principle

**Never touch system Python. Use Homebrew Python and uv for development.**
