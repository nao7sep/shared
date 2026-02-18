# Multi-Project Workflow: Managing 5+ Projects Simultaneously

This document describes a setup for working on multiple projects simultaneously with AI assistance.

## The Vision

Wake up, open 5 terminals, run AI CLI in each, give instructions, monitor diffs in one place, review, commit. Focus on WHAT to build, not HOW to build it.

**Key enablers**:
- Shared guidelines and tools across projects
- Centralized development configuration
- Multi-project workspace in VSCode
- Efficient terminal management (tmux)
- AI doing the implementation

## Folder Structure

```
~/code/
├── shared/                          # Common repo (git)
│   ├── guidelines/                   # Coding standards
│   │   ├── README.md
│   │   ├── python-style.md
│   │   ├── typescript-style.md
│   │   ├── fastapi-patterns.md
│   │   ├── react-patterns.md
│   │   └── git-workflow.md
│   ├── templates/                    # Project templates
│   │   ├── fastapi-react/           # Cookiecutter template
│   │   │   ├── cookiecutter.json
│   │   │   └── {{cookiecutter.project_name}}/
│   │   └── python-lib/
│   ├── scripts/                      # Shared utilities
│   │   ├── scripts/
│   │   │   ├── new-project.sh       # Create project from template
│   │   │   ├── setup-dev.sh         # Setup dev environment
│   │   │   └── generate-types.sh    # Generate TS from Pydantic
│   │   └── config/                   # Shared configs
│   │       ├── .ruff.toml           # Python linter
│   │       ├── .eslintrc.json       # TS linter
│   │       └── .prettierrc
│   └── docs/                         # Shared documentation
│       └── transition-guide/         # This guide
│
├── secrets/                          # Sensitive data (NOT in git)
│   └── dev-config/                   # Development credentials
│       ├── README.md                 # Usage instructions
│       ├── project-a-config.json
│       ├── project-b-config.json
│       └── shared-api-keys.json      # Keys used across projects
│
├── project-a/                        # Individual projects
├── project-b/
├── project-c/
├── project-d/
├── project-e/
└── ...
```

## One-Time Setup

### 1. Create Shared Repository

```bash
mkdir -p ~/code/shared/{guidelines,templates,scripts/{bin,config},docs}
cd ~/code/shared
git init
```

Create `README.md`:

```markdown
# Shared Development Resources

Common guidelines, templates, and tools for all projects.

## Contents

- **guidelines/**: Coding standards and patterns
- **templates/**: Project templates (use cookiecutter/copier)
- **scripts/**: Scripts and shared configurations
- **docs/**: Documentation including transition guide

## Usage

New projects should reference these guidelines. When you establish
a pattern worth reusing, document it here.
```

### 2. Create Secrets Directory

```bash
mkdir -p ~/code/secrets/dev-config
cd ~/code/secrets
echo "*" > .gitignore  # Never commit
```

Create `~/code/secrets/dev-config/README.md`:

```markdown
# Development Secrets

Sensitive configuration and credentials for development environments.

## Structure

Each project has a JSON file with credentials and API keys:
- `project-name-config.json`: Project-specific config
- `shared-api-keys.json`: Keys used across multiple projects

## Usage in Projects

In your `backend/app/core/config.py`:

```python
from pathlib import Path
import json
import os

DEV_CONFIG_PATH = Path.home() / "code" / "secrets" / "dev-config"

class Settings:
    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "development")

        if self.environment == "development":
            self._load_dev_config()
        else:
            self._load_from_env()

    def _load_dev_config(self):
        config_file = DEV_CONFIG_PATH / f"{PROJECT_NAME}-config.json"
        if config_file.exists():
            with open(config_file) as f:
                config = json.load(f)
                self.database_url = config.get("database_url")
                self.secret_key = config.get("secret_key")
                # ... other settings
        else:
            raise FileNotFoundError(f"Dev config not found: {config_file}")

    def _load_from_env(self):
        self.database_url = os.getenv("DATABASE_URL")
        self.secret_key = os.getenv("SECRET_KEY")
        # ... other settings

settings = Settings()
```

## Security Notes

- This directory is for DEVELOPMENT only
- Use environment variables or key stores in production
- Never commit this to git
```

Example config file (`~/code/secrets/dev-config/project-a-config.json`):

```json
{
  "database_url": "postgresql://localhost/project_a_dev",
  "secret_key": "dev-secret-key-change-in-production",
  "stripe_api_key": "sk_test_...",
  "redis_url": "redis://localhost:6379/0"
}
```

### 3. Install tmux (Terminal Multiplexer)

```bash
brew install tmux
```

Create `~/.tmux.conf`:

```bash
# Improve colors
set -g default-terminal "screen-256color"

# Change prefix to Ctrl-a (easier to type)
unbind C-b
set -g prefix C-a
bind C-a send-prefix

# Split panes with | and -
bind | split-window -h
bind - split-window -v

# Switch panes with Alt+arrow (no prefix needed)
bind -n M-Left select-pane -L
bind -n M-Right select-pane -R
bind -n M-Up select-pane -U
bind -n M-Down select-pane -D

# Switch windows with Shift+arrow
bind -n S-Left previous-window
bind -n S-Right next-window

# Enable mouse mode
set -g mouse on

# Start window numbering at 1
set -g base-index 1
```

### 4. Create tmux Startup Script

Create `~/code/start-dev-session.sh`:

```bash
#!/bin/bash

# Start a tmux session with 5 project windows
SESSION_NAME="dev"

# Kill existing session if it exists
tmux has-session -t $SESSION_NAME 2>/dev/null && tmux kill-session -t $SESSION_NAME

# Create new session with first project
tmux new-session -d -s $SESSION_NAME -n project-a -c ~/code/project-a

# Create windows for other projects
tmux new-window -t $SESSION_NAME: -n project-b -c ~/code/project-b
tmux new-window -t $SESSION_NAME: -n project-c -c ~/code/project-c
tmux new-window -t $SESSION_NAME: -n project-d -c ~/code/project-d
tmux new-window -t $SESSION_NAME: -n project-e -c ~/code/project-e

# Select first window
tmux select-window -t $SESSION_NAME:0

# Attach to session
tmux attach-session -t $SESSION_NAME
```

Make it executable:

```bash
chmod +x ~/code/start-dev-session.sh
```

### 5. Create VSCode Workspace

Create `~/code/active-projects.code-workspace`:

```json
{
  "folders": [
    {
      "name": "Project A",
      "path": "project-a"
    },
    {
      "name": "Project B",
      "path": "project-b"
    },
    {
      "name": "Project C",
      "path": "project-c"
    },
    {
      "name": "Project D",
      "path": "project-d"
    },
    {
      "name": "Project E",
      "path": "project-e"
    },
    {
      "name": "Shared",
      "path": "shared"
    }
  ],
  "settings": {
    "files.exclude": {
      "**/__pycache__": true,
      "**/node_modules": true,
      "**/.pytest_cache": true,
      "**/dist": true,
      "**/build": true
    },
    "search.exclude": {
      "**/node_modules": true,
      "**/dist": true,
      "**/.venv": true
    },
    "python.linting.enabled": true,
    "python.linting.ruffEnabled": true,
    "editor.formatOnSave": true,
    "python.formatting.provider": "black",
    "[typescript]": {
      "editor.defaultFormatter": "esbenp.prettier-vscode"
    },
    "[typescriptreact]": {
      "editor.defaultFormatter": "esbenp.prettier-vscode"
    }
  }
}
```

Open with: `code ~/code/active-projects.code-workspace`

## Daily Workflow

### Morning Routine (5 minutes)

1. **Start tmux session**:
   ```bash
   ~/code/start-dev-session.sh
   ```

2. **Open VSCode workspace**:
   ```bash
   code ~/code/active-projects.code-workspace
   ```

3. **Start AI CLI in each tmux window**:
   - Switch to each window (Ctrl-a, then 0-4)
   - Run: `claude-code` (or your AI CLI command)

4. **You now have**:
   - 5 tmux windows, each in a different project directory
   - AI CLI running in each window
   - VSCode showing all projects with unified Source Control

### Working on Multiple Projects

**In each tmux window (Ctrl-a, then number to switch)**:

```
# Project A window
You: "Implement user authentication according to docs/api.md"
AI: [implements]
You: "Add rate limiting to login endpoint"
AI: [implements]

# Project B window (Ctrl-a, 2)
You: "Create product listing page with pagination"
AI: [implements]
You: "Add search filtering"
AI: [implements]

# Continue rotating through projects
```

**In VSCode**:
- Source Control panel shows ALL changes across all projects
- Review diffs for all projects in one place
- Use Cmd+1, Cmd+2, etc. to switch between project folders
- Commit changes per project

### tmux Cheat Sheet

**Navigation**:
- `Ctrl-a, 0-4`: Switch to window 0-4 (your projects)
- `Ctrl-a, c`: Create new window
- `Ctrl-a, ,`: Rename current window
- `Ctrl-a, d`: Detach from session (keeps running)

**Re-attach later**:
```bash
tmux attach -t dev
```

**Exit tmux**:
```bash
# In tmux
exit  # In each window, or:
Ctrl-a, :kill-session
```

## Shared Guidelines

### Creating Guidelines

When you establish a pattern worth reusing, document it:

**Example**: `~/code/shared/guidelines/fastapi-patterns.md`

```markdown
# FastAPI Patterns

## Dependency Injection

Always use FastAPI's `Depends()` for shared resources:

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session

@router.get("/users")
async def get_users(db: AsyncSession = Depends(get_db)):
    # Use db session
    pass
```

## Error Handling

Use `HTTPException` with appropriate status codes:

```python
from fastapi import HTTPException, status

if not user:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found"
    )
```

## Authentication

Use dependency injection for current user:

```python
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    # Verify token, fetch user
    pass

@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
```
```

### Using Guidelines

**Tell AI to follow them**:

```
Implement the registration endpoint following the patterns
in ~/code/shared/guidelines/fastapi-patterns.md
```

AI will read the guidelines and apply them.

## Production Secret Management

**Development**: Use `~/code/secrets/dev-config/` as documented

**Production**: Use one of these approaches:

### Option 1: Environment Variables (Simplest)

```bash
# In production environment
export DATABASE_URL="postgresql://..."
export SECRET_KEY="..."
```

In code, settings loads from env vars when not in development mode.

### Option 2: macOS Keychain (More Secure for Local)

```python
import keyring

# Store once (manually or in setup script)
keyring.set_password("project-a", "database_url", "postgresql://...")
keyring.set_password("project-a", "secret_key", "...")

# In your config.py
class Settings:
    def __init__(self):
        if self.environment == "production":
            self.database_url = keyring.get_password("project-a", "database_url")
            self.secret_key = keyring.get_password("project-a", "secret_key")
```

### Option 3: Cloud Secret Managers

- AWS Secrets Manager
- Google Cloud Secret Manager
- Azure Key Vault
- HashiCorp Vault

Use these in deployed environments, not for local development.

## Project Templates

Create a template for new projects to ensure consistency:

### Install Cookiecutter

```bash
brew install cookiecutter
```

### Create Template

`~/code/shared/templates/fastapi-react/cookiecutter.json`:

```json
{
  "project_name": "my-project",
  "project_slug": "{{ cookiecutter.project_name.lower().replace(' ', '-') }}",
  "backend_port": "8000",
  "database_name": "{{ cookiecutter.project_slug.replace('-', '_') }}_dev"
}
```

Then create the template structure following the pattern in `02-project-setup.md`.

### Use Template

```bash
cd ~/code
cookiecutter shared/templates/fastapi-react/
# Answer prompts
# Project created with all the structure ready
```

## Scaling Beyond 5 Projects

**When managing 10+ projects**:

1. **Group by status**:
   - Active workspace: 5 projects you're working on this week
   - Maintenance workspace: Projects you check occasionally
   - Archived: Completed projects

2. **Rotate projects**:
   - Update `active-projects.code-workspace` weekly
   - Update `start-dev-session.sh` to match

3. **Use project management**:
   - Simple markdown file: `~/code/shared/projects.md`
   - List active projects, their status, next actions

## Tips and Best Practices

### Keep Commits Separate

Commit each project independently. Don't create cross-project commits unless they're truly related.

### Sync Shared Guidelines

When you update `shared/guidelines/`, notify all project AI sessions:

```
Note: I've updated the authentication pattern in shared/guidelines.
Please re-read it before implementing new auth code.
```

### Use Consistent Naming

- Projects: `kebab-case` (project-name)
- Python modules: `snake_case` (module_name)
- TypeScript files: `PascalCase.tsx` for components, `camelCase.ts` for utilities
- Config files: Project name prefix (`project-a-config.json`)

### Monitor Resources

Running 5 development servers + 5 AI sessions can use significant resources:

- Close unused project servers
- Use lightweight databases for dev (SQLite when possible)
- Consider running backend servers only when actively testing

### Daily Standup with Yourself

At end of day, review what you accomplished:

```markdown
# 2026-01-30

## Project A
- Implemented user registration
- Added email verification

## Project B
- Created product listing UI
- Fixed pagination bug

## Project C
- Started payment integration
- Need to finish Stripe webhooks tomorrow

## Blockers
- Project D needs design mockups before continuing
```

Save in `~/code/shared/daily-notes/2026-01-30.md`

## Summary

**Setup once**:
- `shared/` repository for guidelines and tools
- `secrets/` directory for development config
- tmux script for multi-terminal management
- VSCode workspace for unified view

**Daily workflow**:
1. Start tmux session (all projects)
2. Open VSCode workspace (unified diff view)
3. Give AI instructions in each project
4. Review and commit changes
5. Rotate between projects efficiently

**Key principle**: Standardize the structure, customize the content. Every project follows the same patterns, making context-switching effortless.
