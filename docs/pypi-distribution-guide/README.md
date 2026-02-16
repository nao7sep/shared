# Python Package Distribution to PyPI

A practical guide for publishing Python applications to PyPI, based on real experience setting up package distribution for a CLI application in a monorepo environment.

## Reading Order

This guide is structured as an ordered learning path:

1. **[01-basics.md](01-basics.md)** - PyPI fundamentals, TestPyPI vs PyPI, version numbering, and what gets packaged
2. **[02-setup.md](02-setup.md)** - One-time setup: accounts, tokens, Poetry configuration
3. **[03-publishing.md](03-publishing.md)** - The publishing workflow: building and uploading packages
4. **[04-installation.md](04-installation.md)** - Installing packages with pip vs pipx, testing installations
5. **[05-automation.md](05-automation.md)** - Creating helper scripts for the release process
6. **[06-best-practices.md](06-best-practices.md)** - Dependency management, version constraints, common pitfalls

## Who This Is For

- Python developers publishing their first package to PyPI
- Developers transitioning from other languages' package ecosystems
- Anyone setting up manual (script-assisted) distribution vs full CI/CD automation
- Teams working in monorepos with multiple Python applications

## Context

This guide focuses on:
- **Poetry** as the build/publish tool
- **Manual publishing workflow** (with helper scripts) instead of GitHub Actions
- **CLI applications** specifically (not libraries)
- **pipx** as the recommended installation method
- Monorepo-friendly approaches

If you need GitHub Actions automation or library-specific guidance, those topics are noted but not the primary focus.

## Quick Start

If you're already familiar with PyPI basics:
1. Skip to [02-setup.md](02-setup.md) for account/token setup
2. Review [03-publishing.md](03-publishing.md) for the publishing workflow
3. Check [05-automation.md](05-automation.md) for the helper script

## Assumptions

- You have a Python project using Poetry
- Your project structure follows: `apps/your-app/pyproject.toml`
- You're comfortable with command-line tools
- You want manual control over releases (not full automation)
