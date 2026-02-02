# PolyChat - Implementation Plan

## Project Overview

PolyChat is a multi-AI CLI chat tool designed for careful, long-term thinking with git-version-controlled conversation logs. Unlike code-focused AI tools, PolyChat enables deep conversations across multiple AI providers with full conversation management, retry capabilities, and time-travel features.

**Primary Goals**:
1. Learn major AI provider SDKs (OpenAI, Gemini, Claude, Grok, Perplexity, Mistral, DeepSeek)
2. Master API key management best practices
3. Support long-term, version-controlled conversations
4. Enable thoughtful interaction (not just quick coding tasks)

**Scope Limitations**:
- Conversation log management (load/save)
- Send messages to AI providers
- Receive and display responses
- Retry loop (ask different AIs/prompts without deleting history)
- Time travel (delete message and all following)
- NO code execution, NO file operations, NO web browsing

## Project Structure

```
poly-chat/
├── src/
│   └── poly_chat/
│       ├── __init__.py
│       ├── __main__.py              # Entry point for `python -m poly_chat`
│       ├── cli.py                   # REPL loop, main entry
│       ├── profile.py               # Profile loading, path mapping
│       ├── conversation.py          # Conversation data management
│       ├── message_formatter.py     # Line arrays, trimming, JSON serialization
│       ├── commands.py              # Command execution logic
│       ├── streaming.py             # Async streaming response handling
│       ├── models.py                # Model list, AI provider mapping
│       ├── keys/                    # API key management modules
│       │   ├── __init__.py
│       │   ├── loader.py            # Unified key loading interface
│       │   ├── keychain.py          # macOS Keychain access
│       │   ├── env_vars.py          # Environment variable loading
│       │   └── json_files.py        # JSON file key loading
│       └── ai/                      # AI provider implementations
│           ├── __init__.py
│           ├── base.py              # Shared interface/protocol
│           ├── openai_provider.py   # OpenAI (GPT)
│           ├── claude_provider.py   # Anthropic (Claude)
│           ├── gemini_provider.py   # Google (Gemini)
│           ├── grok_provider.py     # xAI (Grok)
│           ├── perplexity_provider.py # Perplexity
│           ├── mistral_provider.py  # Mistral AI
│           └── deepseek_provider.py # DeepSeek
├── tests/
│   ├── __init__.py
│   ├── conftest.py                  # pytest fixtures
│   ├── test_profile.py
│   ├── test_conversation.py
│   ├── test_message_formatter.py
│   ├── test_commands.py
│   ├── test_keys/
│   │   ├── test_loader.py
│   │   ├── test_keychain.py
│   │   ├── test_env_vars.py
│   │   └── test_json_files.py
│   └── test_ai/
│       ├── test_base.py
│       └── test_providers.py        # Mocked tests
├── system-prompts/                  # Predefined system prompts
│   ├── default.txt
│   ├── critic.txt
│   ├── helpful.txt
│   └── concise.txt
├── pyproject.toml
├── README.md
├── WHAT.md
├── HOW.md
└── .gitignore
```

## Naming Conventions

**Folders**:
- Top-level project: `poly-chat` (hyphen)
- Python package: `poly_chat` (underscore)
- Subfolders: `keys`, `ai` (lowercase, no separators)

**CLI Command**:
- Installed command: `pc`
- Alternative: `polychat` (if `pc` conflicts)

**Files**:
- Python modules: `snake_case.py`
- Config files: `kebab-case.json`
- System prompts: `lowercase.txt`

**Conversation Files**:
- User-specified: any valid filename
- Auto-generated: `poly-chat_<uuid>.json`
- Example: `poly-chat_a1b2c3d4-e5f6-7890-abcd-ef1234567890.json`

## Dependencies

**Python Version**: 3.11+ (for async, zoneinfo, modern type hints)

**Core Dependencies** (pyproject.toml):
```toml
[tool.poetry.dependencies]
python = "^3.11"
prompt-toolkit = "^3.0"      # Rich multiline input
openai = "^1.0"              # OpenAI API
anthropic = "^0.18"          # Claude API
google-generativeai = "^0.4" # Gemini API
# Add other AI SDKs as available

[tool.poetry.group.dev.dependencies]
pytest = "^8.0"
pytest-asyncio = "^0.23"
pytest-mock = "^3.12"
black = "^24.0"
ruff = "^0.2"
mypy = "^1.8"

[tool.poetry.scripts]
pc = "poly_chat.cli:main"
```

**Why These Dependencies**:
- `prompt-toolkit`: Industry-standard for rich CLI input (multiline, history, keybindings)
- Official AI SDKs: Learn each provider's Python SDK properly
- `pytest-asyncio`: Test async code
- `pytest-mock`: Mock AI SDK calls for unit tests

## Installation & Usage

**Installation**:
```bash
cd poly-chat
poetry install
```

**Running**:
```bash
# Via poetry
poetry run pc -p ~/my-profile.json

# After installation (if in PATH)
pc -p ~/my-profile.json

# With chat file specified
pc -p ~/my-profile.json -c ~/chats/strategy.json

# With logging
pc -p ~/my-profile.json -c ~/chats/strategy.json -l debug.log
```

**First-time Setup**:
```bash
# Create new profile (interactive)
pc new ~/my-profile.json

# This creates profile with:
# - System timezone
# - Default AI (user selects from list)
# - Default model per AI (user enters or uses defaults)
# - Conversations directory (user enters or uses ~/poly-chat-logs)
# - Log directory (user enters or uses ~/poly-chat-logs/logs)
# - API key configuration prompts
```

## Data Models & File Formats

### Profile File (JSON)

**Location**: User-specified (e.g., `~/poly-chat-profile.json`)

**Structure**:
```json
{
  "default_ai": "claude",
  "models": {
    "openai": "gpt-4",
    "claude": "claude-sonnet-4",
    "gemini": "gemini-2.0-flash",
    "grok": "grok-2",
    "perplexity": "sonar-pro",
    "mistral": "mistral-large",
    "deepseek": "deepseek-chat"
  },
  "system_prompt": "@/system-prompts/default.txt",
  "conversations_dir": "~/poly-chat-logs",
  "log_dir": "~/poly-chat-logs/logs",
  "api_keys": {
    "openai": {
      "type": "env",
      "key": "OPENAI_API_KEY"
    },
    "claude": {
      "type": "keychain",
      "service": "poly-chat",
      "account": "claude-api-key"
    },
    "gemini": {
      "type": "json",
      "path": "~/.secrets/api-keys.json",
      "key": "gemini"
    }
  }
}
```

**Field Descriptions**:

- `default_ai`: Default AI provider to use (openai, claude, gemini, grok, perplexity, mistral, deepseek)
- `models`: Default model for each AI provider
- `system_prompt`: Path to default system prompt file (supports @, ~, absolute)
  - Can also be `null` for no system prompt
  - Can be direct text: `{"type": "text", "content": "You are a helpful assistant"}`
- `conversations_dir`: Default directory for conversation files
- `log_dir`: Default directory for log files
- `api_keys`: API key configuration per provider
  - `type: "env"`: Load from environment variable
  - `type: "keychain"`: Load from macOS Keychain
  - `type: "json"`: Load from JSON file

**Path Mapping Rules** (same as tk):
- `~` or `~/...` → User home directory
- `@` or `@/...` → App root directory (where pyproject.toml is)
- Absolute paths → Used as-is
- Relative paths without prefix → **Error** (current directory is unreliable)

### Conversation File (JSON)

**Location**: User-specified or auto-generated in `conversations_dir`

**Structure**:
```json
{
  "metadata": {
    "title": "Business Strategy 2026",
    "summary": "Long-term planning discussion with focus on market expansion",
    "system_prompt_key": "@/system-prompts/critic.txt",
    "default_model": "claude-sonnet-4",
    "created_at": "2026-02-02T10:00:00.123456Z",
    "updated_at": "2026-02-02T15:30:45.789012Z"
  },
  "messages": [
    {
      "role": "user",
      "content": [
        "What are the key considerations for",
        "expanding into the Asian market?"
      ],
      "timestamp": "2026-02-02T10:00:00.123456Z"
    },
    {
      "role": "assistant",
      "content": [
        "Here are the main factors to consider:",
        "",
        "1. Market Research",
        "   - Cultural differences",
        "   - Local competition",
        "",
        "2. Regulatory Environment",
        "   - Compliance requirements",
        "   - Tax implications"
      ],
      "timestamp": "2026-02-02T10:00:05.789012Z",
      "model": "claude-sonnet-4-20250514"
    },
    {
      "role": "error",
      "content": [
        "API Error: Rate limit exceeded (429)",
        "Retry after: 30 seconds"
      ],
      "timestamp": "2026-02-02T10:05:00.123456Z",
      "details": {
        "provider": "openai",
        "model": "gpt-4",
        "error_type": "rate_limit",
        "retry_after": 30
      }
    }
  ]
}
```

**Metadata Fields**:
- `title`: User-defined or AI-generated conversation title (optional)
- `summary`: User-defined or AI-generated summary (optional)
- `system_prompt_key`: Path/key to system prompt used (preserves integrity)
- `default_model`: Last used model
- `created_at`: Timestamp of first user message
- `updated_at`: Timestamp of last modification

**Message Fields**:
- `role`: "user", "assistant", or "error"
- `content`: Array of strings (one per line)
- `timestamp`: ISO 8601 UTC with microseconds (6 decimal places)
- `model`: AI model that generated the response (assistant messages only)
- `details`: Additional error information (error messages only)

**JSON Formatting Rules**:

1. **UTF-8 without BOM**: Always use `encoding="utf-8"` without BOM
2. **Ensure CJK support**: Use `ensure_ascii=False` in `json.dump()`
3. **Pretty printing**: Use `indent=2` for git-friendliness
4. **Array formatting**: Each array item on separate line

Example of proper JSON output:
```python
with open(path, "w", encoding="utf-8") as f:
    json.dump(
        data,
        f,
        indent=2,
        ensure_ascii=False  # Allows CJK characters
    )
```

**Line Array Format**:

Messages are split by `\n` into arrays. Each line is a separate string:

```python
# Input from user
user_input = """First line
Second line

Fourth line (after empty line)"""

# Stored as
content = [
    "First line",
    "Second line",
    "",
    "Fourth line (after empty line)"
]
```

**Empty lines preserved as `""`**. Never drop them (they're intentional formatting).

**Trimming Rules**:

Before storing, remove leading and trailing whitespace-only lines:

```python
# Input
"""

First line
Second line

"""

# After trimming
[
  "First line",
  "Second line"
]
```

Algorithm:
1. Find first line with non-whitespace content → start
2. Find last line with non-whitespace content → end
3. Keep lines from start to end (inclusive)
4. **Do NOT** reduce consecutive empty lines within content (user's intent)

### System Prompt Files

**Location**: `@/system-prompts/` (shipped with app) or user-defined paths

**Format**: Plain text files, UTF-8 encoding

**Example** (`@/system-prompts/critic.txt`):
```
You are a thoughtful critic who challenges assumptions and identifies potential flaws in reasoning. Be direct but respectful. Focus on helping the user think more deeply about their ideas.
```

**Example** (`@/system-prompts/helpful.txt`):
```
You are a helpful, friendly assistant. Provide clear, concise answers. When the user asks for explanations, break complex topics into understandable parts.
```

**Usage in Profile**:
```json
{
  "system_prompt": "@/system-prompts/critic.txt"
}
```

**Usage in Conversation**:
```json
{
  "metadata": {
    "system_prompt_key": "@/system-prompts/critic.txt"
  }
}
```

**Key Design Decision**: Store only the *key* (path) to system prompt in conversation logs, not the full text. This:
- Preserves contextual integrity (if prompt changes, log still points to specific version)
- Enables git version control of prompts
- Reduces redundancy in conversation files
- Makes it clear which prompt was used

## Core Modules Overview

### Module Responsibilities

**cli.py** - Main entry point and REPL loop
- Parse command-line arguments (`-p`, `-c`, `-l`)
- Initialize profile, conversation, logging
- Run REPL loop with `prompt_toolkit`
- Dispatch commands to `commands.py`
- Handle Ctrl-C, Ctrl-D gracefully
- One conversation per process (exit app when conversation ends)

**profile.py** - Profile management
- Load profile from JSON
- Validate profile structure
- Map paths (~, @, absolute)
- Create new profile (interactive wizard)
- Provide profile data to other modules

**conversation.py** - Conversation data management
- Load conversation from JSON
- Save conversation to JSON (async)
- Add user message
- Add assistant message
- Add error message
- Delete message and all following (time travel)
- Get conversation context for AI (all messages as provider-specific format)
- Update metadata (title, summary, etc.)

**message_formatter.py** - Message formatting utilities
- Convert multiline string to line array
- Trim leading/trailing whitespace-only lines
- Convert line array to string (for display)
- JSON serialization with proper formatting

**commands.py** - Command execution
- Parse command string (identify command, extract args)
- Execute commands: `/model`, `/gpt`, `/retry`, `/delete`, `/title`, `/safe`, etc.
- Coordinate between modules (profile, conversation, AI providers)
- Handle command errors gracefully

**streaming.py** - Async streaming response handling
- Display streaming responses in real-time
- Handle streaming errors mid-response
- Accumulate full response for storage
- Support cancellation (Ctrl-C during stream)

**models.py** - Model registry
- Maintain list of all supported models
- Map model names to AI providers
- Provide model suggestions for autocomplete
- Enable smart `/model` switching (auto-detect provider)

**keys/ (subfolder)** - API key management

**keys/loader.py** - Unified interface
- Load API key based on profile config
- Try multiple methods with fallback
- Validate key (basic checks)
- Return key or raise clear error

**keys/env_vars.py** - Environment variable loading
- Read from `os.environ`
- Support custom variable names

**keys/keychain.py** - macOS Keychain access
- Use `keyring` package
- Read from Keychain
- Handle Keychain errors (requires user approval on first access)

**keys/json_files.py** - JSON file loading
- Load JSON file, extract key by path
- Support nested keys (e.g., `openai.api_key`)
- Handle file not found, malformed JSON

**ai/ (subfolder)** - AI provider implementations

**ai/base.py** - Shared interface (Protocol)
```python
from typing import Protocol, AsyncIterator

class AIProvider(Protocol):
    async def send_message(
        self,
        messages: list[dict],
        model: str,
        stream: bool = True
    ) -> AsyncIterator[str]:
        """Send message to AI, yield response chunks if streaming."""
        ...

    async def get_full_response(
        self,
        messages: list[dict],
        model: str
    ) -> str:
        """Get full response (non-streaming)."""
        ...

    def format_messages(
        self,
        conversation_messages: list[dict],
        system_prompt: str | None
    ) -> list[dict]:
        """Convert conversation format to provider-specific format."""
        ...
```

**ai/openai_provider.py** - OpenAI implementation
- Use `openai` package
- Handle GPT-specific message format
- Support streaming
- Extract token usage from response
- Calculate costs

**ai/claude_provider.py** - Claude implementation
- Use `anthropic` package
- Handle Claude-specific message format (system prompt separate)
- Support streaming
- Extract token usage
- Calculate costs

**ai/gemini_provider.py** - Gemini implementation
- Use `google-generativeai` package
- Handle Gemini-specific format
- Support streaming
- Extract token usage
- Calculate costs

(Similar for other providers: grok, perplexity, mistral, deepseek)

### Module Dependencies

```
cli.py
├─> profile.py
├─> conversation.py
│   └─> message_formatter.py
├─> commands.py
│   ├─> conversation.py
│   ├─> ai/base.py
│   ├─> ai/openai_provider.py (etc.)
│   ├─> streaming.py
│   └─> models.py
├─> keys/loader.py
│   ├─> keys/env_vars.py
│   ├─> keys/keychain.py
│   └─> keys/json_files.py
└─> logging (stdlib)
```

**Key Principle**: Separate concerns clearly. Conversation management doesn't know about AI providers. AI providers don't know about commands. Keys module is completely isolated.

## Profile & Path Mapping (profile.py)

### Core Functions

**`map_path(path: str, base_dir: str) -> str`**

Maps relative paths with special prefixes to absolute paths.

```python
from pathlib import Path

def map_path(path: str, base_dir: str) -> str:
    """Map path with special prefixes to absolute path.

    Args:
        path: Path to map (can have ~, @, or be absolute/relative)
        base_dir: Base directory for relative paths (usually profile dir)

    Returns:
        Absolute path string

    Raises:
        ValueError: If path is relative without special prefix
    """
    # Handle tilde (home directory)
    if path.startswith("~/"):
        return str(Path.home() / path[2:])
    elif path == "~":
        return str(Path.home())

    # Handle @ (app root directory)
    elif path.startswith("@/"):
        # App root is where pyproject.toml is (poly-chat/)
        app_root = Path(__file__).parent.parent.parent
        return str(app_root / path[2:])
    elif path == "@":
        app_root = Path(__file__).parent.parent.parent
        return str(app_root)

    # Absolute path - use as-is
    elif Path(path).is_absolute():
        return str(Path(path))

    # Relative path without prefix - ERROR
    else:
        raise ValueError(
            f"Relative paths without prefix are not supported: {path}\n"
            f"Use '~/' for home directory, '@/' for app directory, "
            f"or provide absolute path"
        )
```

**`load_profile(path: str) -> dict`**

Load and validate profile from JSON file.

```python
import json
from pathlib import Path
from typing import Any

def load_profile(path: str) -> dict[str, Any]:
    """Load profile from JSON file.

    Args:
        path: Path to profile file (can have ~, absolute)

    Returns:
        Profile dictionary with absolute paths

    Raises:
        FileNotFoundError: If profile doesn't exist
        ValueError: If profile structure is invalid
        json.JSONDecodeError: If JSON is malformed
    """
    # Expand ~ if present
    profile_path = Path(path).expanduser().resolve()

    if not profile_path.exists():
        raise FileNotFoundError(
            f"Profile not found: {profile_path}\n"
            f"Create a new profile with: pc new {path}"
        )

    # Load JSON
    with open(profile_path, "r", encoding="utf-8") as f:
        profile = json.load(f)

    # Validate required fields
    validate_profile(profile)

    # Map all path fields
    profile_dir = str(profile_path.parent)
    profile["conversations_dir"] = map_path(
        profile["conversations_dir"],
        profile_dir
    )
    profile["log_dir"] = map_path(
        profile["log_dir"],
        profile_dir
    )

    # Map system_prompt if it's a path
    if isinstance(profile["system_prompt"], str):
        profile["system_prompt"] = map_path(
            profile["system_prompt"],
            profile_dir
        )
    # If it's a dict with type="text", leave as-is

    # Map API key paths
    for provider, key_config in profile.get("api_keys", {}).items():
        if key_config.get("type") == "json":
            key_config["path"] = map_path(
                key_config["path"],
                profile_dir
            )

    return profile


def validate_profile(profile: dict[str, Any]) -> None:
    """Validate profile structure.

    Args:
        profile: Profile dictionary

    Raises:
        ValueError: If profile is invalid
    """
    required = [
        "default_ai",
        "models",
        "conversations_dir",
        "log_dir",
        "api_keys"
    ]

    missing = [f for f in required if f not in profile]
    if missing:
        raise ValueError(
            f"Profile missing required fields: {', '.join(missing)}"
        )

    # Validate default_ai is in models
    if profile["default_ai"] not in profile["models"]:
        raise ValueError(
            f"default_ai '{profile['default_ai']}' not found in models"
        )

    # Validate models is a dict
    if not isinstance(profile["models"], dict):
        raise ValueError("'models' must be a dictionary")

    # Validate api_keys structure
    if not isinstance(profile.get("api_keys"), dict):
        raise ValueError("'api_keys' must be a dictionary")
```

**`create_profile(path: str) -> dict`**

Create new profile interactively.

```python
import os
from datetime import datetime

def create_profile(path: str) -> dict[str, Any]:
    """Create new profile with interactive wizard.

    Args:
        path: Where to save the profile

    Returns:
        Created profile dictionary
    """
    profile_path = Path(path).expanduser().resolve()

    # Create directory if needed
    profile_path.parent.mkdir(parents=True, exist_ok=True)

    # Get system timezone
    try:
        local_tz = datetime.now().astimezone().tzinfo
        if hasattr(local_tz, 'key'):
            timezone = local_tz.key
        else:
            timezone = "UTC"
    except Exception:
        timezone = "UTC"

    print(f"Creating new profile: {profile_path}")
    print(f"Detected timezone: {timezone}")
    print()

    # Interactive prompts
    print("Available AI providers:")
    print("  1. OpenAI (GPT)")
    print("  2. Claude (Anthropic)")
    print("  3. Gemini (Google)")
    print("  4. Grok (xAI)")
    print("  5. Perplexity")
    print("  6. Mistral")
    print("  7. DeepSeek")

    provider_map = {
        "1": "openai",
        "2": "claude",
        "3": "gemini",
        "4": "grok",
        "5": "perplexity",
        "6": "mistral",
        "7": "deepseek"
    }

    choice = input("Select default AI (1-7) [2]: ").strip() or "2"
    default_ai = provider_map.get(choice, "claude")

    # Get conversations directory
    default_conv_dir = "~/poly-chat-logs"
    conv_dir = input(
        f"Conversations directory [{default_conv_dir}]: "
    ).strip() or default_conv_dir

    # Get log directory
    default_log_dir = f"{conv_dir}/logs"
    log_dir = input(
        f"Log directory [{default_log_dir}]: "
    ).strip() or default_log_dir

    # Create profile structure
    profile = {
        "default_ai": default_ai,
        "models": {
            "openai": "gpt-4o",
            "claude": "claude-sonnet-4",
            "gemini": "gemini-2.0-flash",
            "grok": "grok-2",
            "perplexity": "sonar-pro",
            "mistral": "mistral-large",
            "deepseek": "deepseek-chat"
        },
        "system_prompt": "@/system-prompts/default.txt",
        "conversations_dir": conv_dir,
        "log_dir": log_dir,
        "api_keys": {}
    }

    # Configure API keys
    print("\nAPI Key Configuration")
    print("Options: [e]nv variable, [k]eychain, [j]son file, [s]kip")

    for provider in profile["models"].keys():
        print(f"\n{provider.upper()} API key:")
        choice = input("  Configure as (e/k/j/s) [s]: ").strip().lower() or "s"

        if choice == "e":
            var_name = input(f"  Environment variable name [" +
                           f"{provider.upper()}_API_KEY]: ").strip()
            var_name = var_name or f"{provider.upper()}_API_KEY"
            profile["api_keys"][provider] = {
                "type": "env",
                "key": var_name
            }

        elif choice == "k":
            service = input(f"  Keychain service [poly-chat]: ").strip() or "poly-chat"
            account = input(f"  Keychain account [{provider}-api-key]: ").strip()
            account = account or f"{provider}-api-key"
            profile["api_keys"][provider] = {
                "type": "keychain",
                "service": service,
                "account": account
            }

        elif choice == "j":
            json_path = input(f"  JSON file path [~/.secrets/api-keys.json]: ").strip()
            json_path = json_path or "~/.secrets/api-keys.json"
            key_name = input(f"  Key in JSON [{provider}]: ").strip() or provider
            profile["api_keys"][provider] = {
                "type": "json",
                "path": json_path,
                "key": key_name
            }

    # Save profile
    with open(profile_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)

    print(f"\nProfile created: {profile_path}")
    return profile
```

### Edge Cases

**Profile doesn't exist**:
- Clear error with suggestion to use `pc new`

**Invalid JSON**:
- Show parse error and file location

**Missing required fields**:
- List all missing fields clearly

**Invalid path mapping**:
- Relative path without prefix → Error with examples
- `@` but can't find app root → Error
- `~` but can't find home → Error (rare)

**API key configuration empty**:
- Allow it (user can configure later or use env vars directly)

## API Key Management (keys/ subfolder)

### Architecture

Separate module for each key storage method. Unified interface in `loader.py`.

**Design principle**: Support multiple storage methods, make it easy to add new ones, isolate key handling from rest of app.

### keys/loader.py - Unified Interface

```python
from typing import Any

def load_api_key(provider: str, config: dict[str, Any]) -> str:
    """Load API key based on configuration.

    Args:
        provider: AI provider name (openai, claude, etc.)
        config: Key configuration from profile

    Returns:
        API key string

    Raises:
        ValueError: If key cannot be loaded

    Example configs:
        {"type": "env", "key": "OPENAI_API_KEY"}
        {"type": "keychain", "service": "poly-chat", "account": "claude-key"}
        {"type": "json", "path": "~/.secrets/keys.json", "key": "gemini"}
    """
    key_type = config.get("type")

    if key_type == "env":
        from .env_vars import load_from_env
        return load_from_env(config["key"])

    elif key_type == "keychain":
        from .keychain import load_from_keychain
        return load_from_keychain(
            config["service"],
            config["account"]
        )

    elif key_type == "json":
        from .json_files import load_from_json
        return load_from_json(
            config["path"],
            config["key"]
        )

    else:
        raise ValueError(
            f"Unknown key type '{key_type}' for provider '{provider}'"
        )


def validate_api_key(key: str, provider: str) -> bool:
    """Basic validation of API key.

    Args:
        key: API key to validate
        provider: Provider name (for provider-specific validation)

    Returns:
        True if key looks valid

    Note: This is basic validation (non-empty, reasonable length).
    Actual validation happens when making API calls.
    """
    if not key or not key.strip():
        return False

    # Most API keys are at least 20 characters
    if len(key.strip()) < 20:
        return False

    return True
```

### keys/env_vars.py - Environment Variables

```python
import os

def load_from_env(var_name: str) -> str:
    """Load API key from environment variable.

    Args:
        var_name: Environment variable name

    Returns:
        API key string

    Raises:
        ValueError: If variable not set or empty
    """
    value = os.environ.get(var_name)

    if not value:
        raise ValueError(
            f"Environment variable '{var_name}' not set.\n"
            f"Set it with: export {var_name}=your-api-key"
        )

    return value.strip()
```

### keys/keychain.py - macOS Keychain

```python
try:
    import keyring
except ImportError:
    keyring = None


def load_from_keychain(service: str, account: str) -> str:
    """Load API key from macOS Keychain.

    Args:
        service: Keychain service name (e.g., "poly-chat")
        account: Keychain account name (e.g., "claude-api-key")

    Returns:
        API key string

    Raises:
        ImportError: If keyring package not installed
        ValueError: If key not found in keychain

    Note: First access will require user approval via macOS system dialog.
    """
    if keyring is None:
        raise ImportError(
            "keyring package not installed.\n"
            "Install with: poetry add keyring"
        )

    try:
        key = keyring.get_password(service, account)
    except Exception as e:
        raise ValueError(
            f"Failed to access keychain: {e}\n"
            f"Service: {service}, Account: {account}"
        )

    if not key:
        raise ValueError(
            f"API key not found in keychain.\n"
            f"Service: {service}, Account: {account}\n"
            f"Add it with: security add-generic-password "
            f"-s {service} -a {account} -w your-api-key"
        )

    return key


def store_in_keychain(service: str, account: str, key: str) -> None:
    """Store API key in macOS Keychain.

    Args:
        service: Keychain service name
        account: Keychain account name
        key: API key to store

    Raises:
        ImportError: If keyring package not installed
        ValueError: If storing fails
    """
    if keyring is None:
        raise ImportError("keyring package not installed")

    try:
        keyring.set_password(service, account, key)
    except Exception as e:
        raise ValueError(f"Failed to store key in keychain: {e}")
```

### keys/json_files.py - JSON File Storage

```python
import json
from pathlib import Path

def load_from_json(file_path: str, key_name: str) -> str:
    """Load API key from JSON file.

    Args:
        file_path: Path to JSON file (already mapped)
        key_name: Key name in JSON (supports nested like "openai.api_key")

    Returns:
        API key string

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If key not found or file invalid

    Example JSON file:
    {
      "openai": "sk-...",
      "claude": "sk-ant-...",
      "nested": {
        "gemini": "..."
      }
    }
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"API key file not found: {file_path}\n"
            f"Create it with appropriate API keys"
        )

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {file_path}: {e}")

    # Support nested keys with dot notation
    value = data
    for part in key_name.split("."):
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            raise ValueError(
                f"Key '{key_name}' not found in {file_path}\n"
                f"Available keys: {', '.join(data.keys())}"
            )

    if not isinstance(value, str):
        raise ValueError(
            f"Key '{key_name}' in {file_path} is not a string"
        )

    return value.strip()
```

### Usage Example

```python
# In cli.py or commands.py

from poly_chat.keys.loader import load_api_key, validate_api_key

# Load key for current provider
provider = session["current_ai"]  # e.g., "openai"
key_config = profile["api_keys"].get(provider)

if not key_config:
    raise ValueError(
        f"No API key configured for {provider}.\n"
        f"Add to profile or set environment variable"
    )

try:
    api_key = load_api_key(provider, key_config)

    if not validate_api_key(api_key, provider):
        raise ValueError(
            f"Invalid API key for {provider} "
            f"(too short or malformed)"
        )

    # Use api_key with AI provider
    # ...

except ValueError as e:
    print(f"Error loading API key: {e}")
    # Logged to error log if -l specified
```

### Error Handling

**Environment variable not set**:
```
Error: Environment variable 'OPENAI_API_KEY' not set.
Set it with: export OPENAI_API_KEY=your-api-key
```

**Keychain access denied**:
```
Error: Failed to access keychain: User denied access
Service: poly-chat, Account: claude-api-key

First-time access requires approval via macOS system dialog.
```

**JSON file not found**:
```
Error: API key file not found: /Users/you/.secrets/api-keys.json
Create it with appropriate API keys
```

**Key not in JSON**:
```
Error: Key 'grok' not found in /Users/you/.secrets/api-keys.json
Available keys: openai, claude, gemini
```

### Security Considerations

**Do NOT**:
- Log API keys (ever)
- Print API keys to console
- Include API keys in error messages
- Store API keys in conversation files

**Do**:
- Use secure storage (Keychain preferred)
- Validate keys before use (basic checks)
- Show partial keys in debug output (e.g., "sk-...xyz" - first 3 and last 3 chars)
- Clear error messages without exposing keys

## Conversation Data Management (conversation.py)

### Core Functions

**`load_conversation(path: str) -> dict`**

```python
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

def load_conversation(path: str) -> dict[str, Any]:
    """Load conversation from JSON file.

    Args:
        path: Path to conversation file (already mapped)

    Returns:
        Conversation dictionary

    Raises:
        FileNotFoundError: If file doesn't exist (should create new)
        ValueError: If JSON is invalid
    """
    conv_path = Path(path)

    if not conv_path.exists():
        # Return empty conversation structure
        return {
            "metadata": {
                "title": None,
                "summary": None,
                "system_prompt_key": None,
                "default_model": None,
                "created_at": None,
                "updated_at": None
            },
            "messages": []
        }

    try:
        with open(conv_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Validate structure
        if "metadata" not in data or "messages" not in data:
            raise ValueError("Invalid conversation file structure")

        return data

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in conversation file: {e}")


async def save_conversation(path: str, data: dict[str, Any]) -> None:
    """Save conversation to JSON file (async).

    Args:
        path: Path to conversation file
        data: Conversation dictionary

    Updates metadata.updated_at before saving.
    """
    import aiofiles

    # Update timestamp
    data["metadata"]["updated_at"] = (
        datetime.now(timezone.utc).isoformat()
    )

    # If created_at not set, set it
    if not data["metadata"]["created_at"]:
        data["metadata"]["created_at"] = data["metadata"]["updated_at"]

    # Ensure directory exists
    conv_path = Path(path)
    conv_path.parent.mkdir(parents=True, exist_ok=True)

    # Write async
    async with aiofiles.open(conv_path, "w", encoding="utf-8") as f:
        # Use json.dumps first (it's not async), then write
        json_str = json.dumps(data, indent=2, ensure_ascii=False)
        await f.write(json_str)
```

**`add_user_message(data: dict, content: str) -> None`**

```python
from poly_chat.message_formatter import text_to_lines

def add_user_message(data: dict[str, Any], content: str) -> None:
    """Add user message to conversation.

    Args:
        data: Conversation dictionary
        content: Message text (multiline string)

    Formats content as line array with trimming.
    """
    lines = text_to_lines(content)

    message = {
        "role": "user",
        "content": lines,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    data["messages"].append(message)
```

**`add_assistant_message(data: dict, content: str, model: str) -> None`**

```python
def add_assistant_message(
    data: dict[str, Any],
    content: str,
    model: str
) -> None:
    """Add assistant message to conversation.

    Args:
        data: Conversation dictionary
        content: Response text
        model: Model that generated the response
    """
    lines = text_to_lines(content)

    message = {
        "role": "assistant",
        "content": lines,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": model
    }

    data["messages"].append(message)
```

**`add_error_message(data: dict, content: str, details: dict | None = None) -> None`**

```python
def add_error_message(
    data: dict[str, Any],
    content: str,
    details: dict[str, Any] | None = None
) -> None:
    """Add error message to conversation.

    Args:
        data: Conversation dictionary
        content: Error description
        details: Additional error information (optional)
    """
    lines = text_to_lines(content)

    message = {
        "role": "error",
        "content": lines,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    if details:
        message["details"] = details

    data["messages"].append(message)
```

**`delete_message_and_following(data: dict, index: int) -> int`**

```python
def delete_message_and_following(data: dict[str, Any], index: int) -> int:
    """Delete message at index and all following messages.

    Args:
        data: Conversation dictionary
        index: Index of message to delete (0-based)

    Returns:
        Number of messages deleted

    Raises:
        IndexError: If index out of range
    """
    messages = data["messages"]

    if index < 0 or index >= len(messages):
        raise IndexError(f"Message index {index} out of range")

    deleted_count = len(messages) - index
    data["messages"] = messages[:index]

    return deleted_count
```

**`update_metadata(data: dict, **kwargs) -> None`**

```python
def update_metadata(data: dict[str, Any], **kwargs) -> None:
    """Update conversation metadata.

    Args:
        data: Conversation dictionary
        **kwargs: Metadata fields to update (title, summary, etc.)

    Example:
        update_metadata(conv, title="New Title", summary="...")
    """
    for key, value in kwargs.items():
        if key in data["metadata"]:
            data["metadata"][key] = value
        else:
            raise ValueError(f"Unknown metadata field: {key}")
```

## Message Formatting (message_formatter.py)

### Core Functions

**`text_to_lines(text: str) -> list[str]`**

```python
def text_to_lines(text: str) -> list[str]:
    """Convert multiline text to line array with trimming.

    Args:
        text: Input text (may have leading/trailing whitespace-only lines)

    Returns:
        List of lines with leading/trailing whitespace-only lines removed

    Algorithm:
    1. Split by \n
    2. Find first non-whitespace-only line
    3. Find last non-whitespace-only line
    4. Return lines in that range
    5. Preserve empty lines within content as ""

    Example:
        Input: "\n\nFirst line\n\nSecond line\n\n"
        Output: ["First line", "", "Second line"]
    """
    lines = text.split("\n")

    # Find first non-whitespace-only line
    start = 0
    for i, line in enumerate(lines):
        if line.strip():  # Has non-whitespace content
            start = i
            break
    else:
        # All lines are whitespace-only
        return []

    # Find last non-whitespace-only line
    end = len(lines)
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip():
            end = i + 1
            break

    return lines[start:end]


def lines_to_text(lines: list[str]) -> str:
    """Convert line array back to text.

    Args:
        lines: List of lines

    Returns:
        Joined text with \n
    """
    return "\n".join(lines)
```

### Usage Example

```python
# User input from prompt_toolkit
user_input = """

What are the key factors
in making this decision?

I want to be thorough.

"""

# Convert to lines (trimmed)
lines = text_to_lines(user_input)
# Result: [
#     "What are the key factors",
#     "in making this decision?",
#     "",
#     "I want to be thorough."
# ]

# Add to conversation
add_user_message(conversation, user_input)

# Later, when displaying
display_text = lines_to_text(message["content"])
print(display_text)
```

## AI Providers Architecture (ai/ subfolder)

### Design Principles

1. **Shared interface**: All providers implement same Protocol
2. **Provider-specific details**: Each provider handles its own message format, API calls, streaming
3. **Async everything**: All API calls are async
4. **Streaming by default**: Support streaming responses
5. **Error handling**: Provider-specific errors converted to standard format

### ai/base.py - Shared Protocol

```python
from typing import Protocol, AsyncIterator
from dataclasses import dataclass


@dataclass
class TokenUsage:
    """Token usage information from API response."""
    input_tokens: int
    output_tokens: int
    total_tokens: int


@dataclass
class CostEstimate:
    """Cost estimate for API call."""
    input_cost: float  # USD
    output_cost: float  # USD
    total_cost: float  # USD


class AIProvider(Protocol):
    """Shared interface for all AI providers."""

    provider_name: str  # "openai", "claude", etc.

    async def send_message_streaming(
        self,
        messages: list[dict],
        model: str,
        system_prompt: str | None = None
    ) -> AsyncIterator[str]:
        """Send message and yield response chunks.

        Args:
            messages: Conversation messages in internal format
            model: Model name
            system_prompt: System prompt text (optional)

        Yields:
            Response chunks as they arrive

        Raises:
            APIError: On API failures
        """
        ...

    async def send_message(
        self,
        messages: list[dict],
        model: str,
        system_prompt: str | None = None
    ) -> tuple[str, TokenUsage]:
        """Send message and get full response (non-streaming).

        Args:
            messages: Conversation messages in internal format
            model: Model name
            system_prompt: System prompt text (optional)

        Returns:
            Tuple of (response_text, token_usage)

        Raises:
            APIError: On API failures
        """
        ...

    def format_messages(
        self,
        messages: list[dict],
        system_prompt: str | None = None
    ) -> dict:
        """Convert internal message format to provider-specific format.

        Args:
            messages: Conversation messages (role, content arrays)
            system_prompt: System prompt text (optional)

        Returns:
            Provider-specific message format

        Each provider has different requirements:
        - OpenAI: system message in messages list
        - Claude: system prompt separate parameter
        - Gemini: roles are "user" and "model"
        """
        ...

    def get_cost_estimate(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str
    ) -> CostEstimate:
        """Calculate cost estimate for token usage.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: Model name

        Returns:
            Cost estimate in USD
        """
        ...


class APIError(Exception):
    """Base exception for API errors."""

    def __init__(
        self,
        message: str,
        provider: str,
        error_type: str,
        details: dict | None = None
    ):
        super().__init__(message)
        self.provider = provider
        self.error_type = error_type
        self.details = details or {}
```

### ai/openai_provider.py - OpenAI (GPT)

```python
from typing import AsyncIterator
import openai
from openai import AsyncOpenAI

from .base import AIProvider, TokenUsage, CostEstimate, APIError


class OpenAIProvider:
    """OpenAI (GPT) provider implementation."""

    provider_name = "openai"

    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)

    async def send_message_streaming(
        self,
        messages: list[dict],
        model: str,
        system_prompt: str | None = None
    ) -> AsyncIterator[str]:
        """Stream response from OpenAI API."""
        formatted = self.format_messages(messages, system_prompt)

        try:
            stream = await self.client.chat.completions.create(
                model=model,
                messages=formatted,
                stream=True
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except openai.APIError as e:
            raise APIError(
                message=str(e),
                provider="openai",
                error_type=e.__class__.__name__,
                details={"status_code": getattr(e, "status_code", None)}
            )

    async def send_message(
        self,
        messages: list[dict],
        model: str,
        system_prompt: str | None = None
    ) -> tuple[str, TokenUsage]:
        """Get full response from OpenAI API."""
        formatted = self.format_messages(messages, system_prompt)

        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=formatted,
                stream=False
            )

            content = response.choices[0].message.content
            usage = TokenUsage(
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens
            )

            return content, usage

        except openai.APIError as e:
            raise APIError(
                message=str(e),
                provider="openai",
                error_type=e.__class__.__name__,
                details={"status_code": getattr(e, "status_code", None)}
            )

    def format_messages(
        self,
        messages: list[dict],
        system_prompt: str | None = None
    ) -> list[dict]:
        """Convert to OpenAI message format.

        OpenAI format:
        [
            {"role": "system", "content": "..."},
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "..."}
        ]
        """
        formatted = []

        # Add system prompt if present
        if system_prompt:
            formatted.append({
                "role": "system",
                "content": system_prompt
            })

        # Convert messages
        for msg in messages:
            # Skip error messages (OpenAI doesn't have error role)
            if msg["role"] == "error":
                continue

            # Join line array to string
            content = "\n".join(msg["content"])

            formatted.append({
                "role": msg["role"],
                "content": content
            })

        return formatted

    def get_cost_estimate(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str
    ) -> CostEstimate:
        """Calculate cost for OpenAI models.

        Prices as of February 2026 (update as needed):
        - GPT-4o: $2.50 / 1M input, $10.00 / 1M output
        - GPT-4o-mini: $0.15 / 1M input, $0.60 / 1M output
        """
        # Prices per million tokens
        prices = {
            "gpt-4o": (2.50, 10.00),
            "gpt-4o-mini": (0.15, 0.60),
            "gpt-4": (30.00, 60.00),
            "gpt-3.5-turbo": (0.50, 1.50)
        }

        # Find matching price (handle model variants)
        input_price, output_price = prices.get(
            model,
            prices.get("gpt-4o")  # Default
        )

        input_cost = (input_tokens / 1_000_000) * input_price
        output_cost = (output_tokens / 1_000_000) * output_price

        return CostEstimate(
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=input_cost + output_cost
        )
```

### ai/claude_provider.py - Claude (Anthropic)

```python
from typing import AsyncIterator
import anthropic
from anthropic import AsyncAnthropic

from .base import AIProvider, TokenUsage, CostEstimate, APIError


class ClaudeProvider:
    """Claude (Anthropic) provider implementation."""

    provider_name = "claude"

    def __init__(self, api_key: str):
        self.client = AsyncAnthropic(api_key=api_key)

    async def send_message_streaming(
        self,
        messages: list[dict],
        model: str,
        system_prompt: str | None = None
    ) -> AsyncIterator[str]:
        """Stream response from Claude API."""
        formatted = self.format_messages(messages, system_prompt=None)

        try:
            # Claude uses system parameter separately
            async with self.client.messages.stream(
                model=model,
                messages=formatted,
                system=system_prompt if system_prompt else anthropic.NOT_GIVEN,
                max_tokens=4096
            ) as stream:
                async for text in stream.text_stream:
                    yield text

        except anthropic.APIError as e:
            raise APIError(
                message=str(e),
                provider="claude",
                error_type=e.__class__.__name__,
                details={"status_code": getattr(e, "status_code", None)}
            )

    async def send_message(
        self,
        messages: list[dict],
        model: str,
        system_prompt: str | None = None
    ) -> tuple[str, TokenUsage]:
        """Get full response from Claude API."""
        formatted = self.format_messages(messages, system_prompt=None)

        try:
            response = await self.client.messages.create(
                model=model,
                messages=formatted,
                system=system_prompt if system_prompt else anthropic.NOT_GIVEN,
                max_tokens=4096
            )

            content = response.content[0].text
            usage = TokenUsage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                total_tokens=response.usage.input_tokens + response.usage.output_tokens
            )

            return content, usage

        except anthropic.APIError as e:
            raise APIError(
                message=str(e),
                provider="claude",
                error_type=e.__class__.__name__,
                details={"status_code": getattr(e, "status_code", None)}
            )

    def format_messages(
        self,
        messages: list[dict],
        system_prompt: str | None = None
    ) -> list[dict]:
        """Convert to Claude message format.

        Claude format (system separate):
        [
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "..."}
        ]
        """
        formatted = []

        for msg in messages:
            if msg["role"] == "error":
                continue

            content = "\n".join(msg["content"])

            formatted.append({
                "role": msg["role"],
                "content": content
            })

        return formatted

    def get_cost_estimate(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str
    ) -> CostEstimate:
        """Calculate cost for Claude models.

        Prices as of February 2026:
        - Claude Sonnet 4: $3.00 / 1M input, $15.00 / 1M output
        - Claude Haiku: $0.80 / 1M input, $4.00 / 1M output
        """
        prices = {
            "claude-sonnet-4": (3.00, 15.00),
            "claude-opus-4": (15.00, 75.00),
            "claude-haiku": (0.80, 4.00)
        }

        input_price, output_price = prices.get(
            model,
            prices.get("claude-sonnet-4")
        )

        input_cost = (input_tokens / 1_000_000) * input_price
        output_cost = (output_tokens / 1_000_000) * output_price

        return CostEstimate(
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=input_cost + output_cost
        )
```

### Other Providers

Similar implementations for:
- **ai/gemini_provider.py**: Uses `google-generativeai`, roles are "user"/"model"
- **ai/grok_provider.py**: Similar to OpenAI (may use OpenAI SDK)
- **ai/perplexity_provider.py**: OpenAI-compatible API
- **ai/mistral_provider.py**: Uses `mistralai` package
- **ai/deepseek_provider.py**: OpenAI-compatible API

Each follows same pattern:
1. Implement streaming and non-streaming methods
2. Convert message format
3. Handle provider-specific errors
4. Calculate costs based on current pricing

## Streaming & Async (streaming.py)

### Design

Display AI responses as they arrive (streaming). Handle cancellation (Ctrl-C). Accumulate full response for storage.

### Core Functions

**`display_streaming_response(stream: AsyncIterator[str]) -> str`**

```python
import asyncio
import sys


async def display_streaming_response(
    stream: AsyncIterator[str]
) -> str:
    """Display streaming response and return full text.

    Args:
        stream: Async iterator of response chunks

    Returns:
        Full response text

    Handles Ctrl-C gracefully (stops streaming, returns partial response).
    """
    full_response = []

    try:
        async for chunk in stream:
            # Display chunk immediately
            print(chunk, end="", flush=True)
            full_response.append(chunk)

    except KeyboardInterrupt:
        # User cancelled with Ctrl-C
        print("\n[Streaming cancelled]")

    except Exception as e:
        # API error mid-stream
        print(f"\n[Error during streaming: {e}]")
        raise

    # Newline after response
    print()

    return "".join(full_response)
```

### Usage in Commands

```python
# In commands.py

async def handle_user_message(
    message: str,
    session: dict,
    profile: dict,
    conversation: dict
) -> None:
    """Send user message to AI and display response."""

    # Add user message to conversation
    add_user_message(conversation, message)

    # Get current AI provider and model
    provider_name = session["current_ai"]
    model = session["current_model"]

    # Load API key
    api_key = load_api_key(provider_name, profile["api_keys"][provider_name])

    # Get provider instance
    provider = get_provider(provider_name, api_key)

    # Load system prompt
    system_prompt = load_system_prompt(
        conversation["metadata"]["system_prompt_key"]
    )

    # Format messages for provider
    try:
        # Send message (streaming)
        print(f"\n{provider_name.upper()} ({model}):\n")

        stream = provider.send_message_streaming(
            conversation["messages"],
            model,
            system_prompt
        )

        response_text = await display_streaming_response(stream)

        # Add assistant response to conversation
        add_assistant_message(conversation, response_text, model)

        # Save conversation
        await save_conversation(session["conversation_path"], conversation)

        # Get token usage and cost estimate (requires non-streaming call or parsing)
        # For now, show estimated tokens
        # TODO: Implement token counting

    except APIError as e:
        # Add error to conversation
        error_msg = f"{e.error_type}: {e}"
        add_error_message(
            conversation,
            error_msg,
            details={
                "provider": e.provider,
                "error_type": e.error_type,
                **e.details
            }
        )

        # Save conversation with error
        await save_conversation(session["conversation_path"], conversation)

        # Log error
        if session.get("logger"):
            session["logger"].error(
                f"API error: {e.provider} - {e.error_type} - {e}"
            )

        print(f"\nError: {error_msg}")
```

## Command System (commands.py + cli.py)

### Command Parsing

Commands start with `/`. Otherwise, text is treated as user message.

**`parse_command(line: str) -> tuple[str | None, list, dict]`**

```python
import shlex


def parse_command(line: str) -> tuple[str | None, list, dict]:
    """Parse command line.

    Args:
        line: Input line from user

    Returns:
        Tuple of (command_name, args, kwargs) or (None, ...) if not a command

    Examples:
        "/model gpt-4" -> ("model", ["gpt-4"], {})
        "/title My Title" -> ("title", ["My", "Title"], {})
        "/gpt" -> ("gpt", [], {})
        "Hello" -> (None, ..., ...)
    """
    line = line.strip()

    # Not a command
    if not line.startswith("/"):
        return None, [], {}

    # Remove leading /
    line = line[1:]

    # Split on whitespace (respecting quotes)
    # Actually, user said NO quote support - just split on whitespace
    parts = line.split()

    if not parts:
        return None, [], {}

    command = parts[0].lower()
    args = parts[1:]

    # No kwargs for now (can add later if needed)
    return command, args, {}
```

### Command Execution

**`execute_command(command: str, args: list, session: dict, profile: dict, conversation: dict) -> bool`**

```python
async def execute_command(
    command: str,
    args: list,
    session: dict,
    profile: dict,
    conversation: dict
) -> bool:
    """Execute command.

    Args:
        command: Command name
        args: Command arguments
        session: Session state
        profile: Profile data
        conversation: Conversation data

    Returns:
        True if should exit app, False otherwise
    """
    # AI switching commands
    if command in ["gpt", "gem", "cla", "grok", "perp", "mist", "deep"]:
        return await cmd_switch_ai(command, session, profile)

    # Model command
    elif command == "model":
        return await cmd_model(args, session, profile)

    # Title commands
    elif command == "title":
        return await cmd_title(args, conversation, session)

    elif command == "ai-title":
        return await cmd_ai_title(conversation, session, profile)

    # Summary commands
    elif command == "summary":
        return await cmd_summary(args, conversation, session)

    elif command == "ai-summary":
        return await cmd_ai_summary(conversation, session, profile)

    # Safe check
    elif command == "safe":
        return await cmd_safe(conversation, session, profile)

    # Delete command
    elif command == "delete":
        return await cmd_delete(args, conversation, session)

    # Retry loop (TODO: implement)
    elif command == "retry":
        return await cmd_retry(session)

    # Help
    elif command == "help":
        return cmd_help()

    # Exit
    elif command in ["exit", "quit"]:
        return True  # Signal exit

    else:
        print(f"Unknown command: /{command}")
        print("Type /help for available commands")
        return False
```

### REPL Loop (cli.py)

**`main()`** - Entry point

```python
import argparse
import asyncio
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings


def main():
    """Main entry point for PolyChat CLI."""

    # Parse arguments
    parser = argparse.ArgumentParser(description="PolyChat - Multi-AI CLI Chat")
    parser.add_argument("-p", "--profile", required=True, help="Profile file path")
    parser.add_argument("-c", "--chat", help="Conversation file path")
    parser.add_argument("-l", "--log", help="Log file path")

    args = parser.parse_args()

    # Run async main
    asyncio.run(async_main(args))


async def async_main(args):
    """Async main function."""

    # Setup logging if specified
    logger = None
    if args.log:
        logger = setup_logging(args.log, profile)

    # Load profile
    try:
        profile = load_profile(args.profile)
    except Exception as e:
        print(f"Error loading profile: {e}")
        return

    # Get conversation path
    if args.chat:
        # User specified path
        conv_path = map_conversation_path(args.chat, profile)
    else:
        # Ask user
        conv_path = await prompt_for_conversation(profile)

    # Load conversation
    try:
        conversation = load_conversation(conv_path)
    except Exception as e:
        print(f"Error loading conversation: {e}")
        return

    # Initialize session
    session = {
        "profile_path": args.profile,
        "conversation_path": conv_path,
        "current_ai": profile["default_ai"],
        "current_model": profile["models"][profile["default_ai"]],
        "logger": logger
    }

    # Display startup info
    print(f"PolyChat - {conv_path}")
    print(f"AI: {session['current_ai']} ({session['current_model']})")
    print(f"Messages: {len(conversation['messages'])}")
    if conversation["metadata"]["title"]:
        print(f"Title: {conversation['metadata']['title']}")
    print()
    print("Type your message (Alt+Enter to send, /help for commands)")
    print()

    # Setup prompt_toolkit
    kb = KeyBindings()

    @kb.add("escape", "enter")  # Alt+Enter to submit
    def submit(event):
        event.current_buffer.validate_and_handle()

    prompt_session = PromptSession(
        multiline=True,
        key_bindings=kb,
        prompt_continuation="... "
    )

    # REPL loop
    while True:
        try:
            # Get user input
            user_input = await prompt_session.prompt_async("You: ")

            if not user_input.strip():
                continue

            # Parse command or message
            command, args, kwargs = parse_command(user_input)

            if command:
                # Execute command
                should_exit = await execute_command(
                    command,
                    args,
                    session,
                    profile,
                    conversation
                )

                if should_exit:
                    break
            else:
                # User message - send to AI
                await handle_user_message(
                    user_input,
                    session,
                    profile,
                    conversation
                )

        except KeyboardInterrupt:
            # Ctrl-C - confirm exit
            confirm = input("\nExit? (y/n): ")
            if confirm.lower() == "y":
                break

        except Exception as e:
            print(f"\nError: {e}")
            if logger:
                logger.error(f"Unexpected error: {e}", exc_info=True)

    # Save before exit
    await save_conversation(session["conversation_path"], conversation)

    print("\nConversation saved. Goodbye!")
```

## All Commands - Detailed Specifications

### AI Switching Commands

**`/gpt`, `/gem`, `/cla`, `/grok`, `/perp`, `/mist`, `/deep`**

Switch to specific AI provider using default model from profile.

```python
async def cmd_switch_ai(shortcut: str, session: dict, profile: dict) -> bool:
    """Switch AI provider.

    Args:
        shortcut: Short command (gpt, gem, etc.)
        session: Session state
        profile: Profile data

    Returns:
        False (don't exit)
    """
    ai_map = {
        "gpt": "openai",
        "gem": "gemini",
        "cla": "claude",
        "grok": "grok",
        "perp": "perplexity",
        "mist": "mistral",
        "deep": "deepseek"
    }

    provider_name = ai_map.get(shortcut)

    if provider_name not in profile["models"]:
        print(f"AI '{provider_name}' not configured in profile")
        return False

    session["current_ai"] = provider_name
    session["current_model"] = profile["models"][provider_name]

    print(f"Switched to {provider_name} ({session['current_model']})")
    return False
```

### Model Command

**`/model [model_name]`**

Show available models or switch model (with smart AI detection).

```python
async def cmd_model(args: list, session: dict, profile: dict) -> bool:
    """Show models or switch model.

    Usage:
        /model              -> Show all models
        /model gpt-4        -> Switch to GPT-4 (auto-detect OpenAI)
        /model gemini-pro   -> Switch to Gemini Pro (auto-detect)

    Smart detection: If model belongs to different AI, switch AI too.
    """
    if not args:
        # Show all models
        print("\nAvailable models:")
        print(f"\nCurrent: {session['current_ai']} - {session['current_model']}")
        print("\nConfigured models:")
        for ai, model in profile["models"].items():
            marker = "* " if ai == session["current_ai"] else "  "
            print(f"{marker}{ai}: {model}")
        return False

    model_name = " ".join(args)

    # Try to detect provider from model name
    provider = detect_provider_from_model(model_name)

    if provider:
        # Smart switch: change both AI and model
        session["current_ai"] = provider
        session["current_model"] = model_name
        print(f"Switched to {provider} ({model_name})")
    else:
        # Just change model for current AI
        session["current_model"] = model_name
        print(f"Model set to {model_name}")

    return False


def detect_provider_from_model(model_name: str) -> str | None:
    """Detect AI provider from model name.

    Returns provider name or None if can't detect.
    """
    model_lower = model_name.lower()

    if "gpt" in model_lower or "o1" in model_lower:
        return "openai"
    elif "claude" in model_lower:
        return "claude"
    elif "gemini" in model_lower:
        return "gemini"
    elif "grok" in model_lower:
        return "grok"
    elif "sonar" in model_lower:
        return "perplexity"
    elif "mistral" in model_lower:
        return "mistral"
    elif "deepseek" in model_lower:
        return "deepseek"

    return None
```

### Title Commands

**`/title [text...]`** - Set or delete title

```python
async def cmd_title(
    args: list,
    conversation: dict,
    session: dict
) -> bool:
    """Set or delete conversation title.

    Usage:
        /title                     -> Delete title (with confirmation)
        /title My Conversation     -> Set title to "My Conversation"
    """
    if not args:
        # Delete title
        if conversation["metadata"]["title"]:
            confirm = input(f"Delete title '{conversation['metadata']['title']}'? (y/n): ")
            if confirm.lower() == "y":
                update_metadata(conversation, title=None)
                await save_conversation(session["conversation_path"], conversation)
                print("Title deleted")
        else:
            print("No title set")
    else:
        # Set title
        title = " ".join(args)
        update_metadata(conversation, title=title)
        await save_conversation(session["conversation_path"], conversation)
        print(f"Title set to: {title}")

    return False
```

**`/ai-title`** - AI-generated title

```python
async def cmd_ai_title(
    conversation: dict,
    session: dict,
    profile: dict
) -> bool:
    """Generate title using AI.

    Sends conversation to current AI with prompt to generate title.
    Shows suggestion, user can accept/edit/reject.
    """
    if not conversation["messages"]:
        print("No messages in conversation yet")
        return False

    print("Generating title...")

    # Get provider
    provider_name = session["current_ai"]
    model = session["current_model"]
    api_key = load_api_key(provider_name, profile["api_keys"][provider_name])
    provider = get_provider(provider_name, api_key)

    # Create title generation prompt
    title_messages = conversation["messages"].copy()
    title_messages.append({
        "role": "user",
        "content": [
            "Generate a concise title (max 60 characters) for this conversation.",
            "Only return the title text, nothing else."
        ],
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

    try:
        # Get title from AI (non-streaming)
        suggested_title, _ = await provider.send_message(
            title_messages,
            model,
            system_prompt=None
        )

        suggested_title = suggested_title.strip()

        # Show suggestion
        print(f"\nSuggested title: {suggested_title}")
        action = input("Accept? (y/n/e to edit): ").lower()

        if action == "y":
            update_metadata(conversation, title=suggested_title)
            await save_conversation(session["conversation_path"], conversation)
            print("Title set")

        elif action == "e":
            edited = input(f"Edit title [{suggested_title}]: ") or suggested_title
            update_metadata(conversation, title=edited)
            await save_conversation(session["conversation_path"], conversation)
            print("Title set")

        else:
            print("Title not set")

    except Exception as e:
        print(f"Error generating title: {e}")

    return False
```

### Summary Commands

**`/summary [text...]`** - Set or delete summary
**`/ai-summary`** - AI-generated summary

(Similar implementation to title commands, but for summary field and with longer prompt: "Generate a 2-3 sentence summary...")

### Safe Command

**`/safe`** - Check for sensitive information

```python
async def cmd_safe(
    conversation: dict,
    session: dict,
    profile: dict
) -> bool:
    """Check conversation for sensitive/unsafe content.

    Sends conversation to AI with safety check prompt.
    Response is shown but NOT saved to conversation.
    """
    if not conversation["messages"]:
        print("No messages to check")
        return False

    print("Checking conversation for sensitive content...\n")

    # Get provider
    provider_name = session["current_ai"]
    model = session["current_model"]
    api_key = load_api_key(provider_name, profile["api_keys"][provider_name])
    provider = get_provider(provider_name, api_key)

    # Create safety check prompt
    safety_messages = conversation["messages"].copy()
    safety_messages.append({
        "role": "user",
        "content": [
            "Analyze this conversation for:",
            "1. Personal identifiable information (PII)",
            "2. API keys, passwords, or credentials",
            "3. Potentially unsafe or inappropriate content",
            "",
            "List any findings clearly. If none found, say 'No issues found'."
        ],
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

    try:
        # Get safety check (streaming for better UX)
        stream = provider.send_message_streaming(
            safety_messages,
            model,
            system_prompt=None
        )

        await display_streaming_response(stream)

        # This response is NOT saved to conversation
        print("\n[Safety check complete - not saved to conversation]")

    except Exception as e:
        print(f"Error during safety check: {e}")

    return False
```

### Delete Command

**`/delete <message_index>`** - Delete message and all following

```python
async def cmd_delete(
    args: list,
    conversation: dict,
    session: dict
) -> bool:
    """Delete message and all following messages.

    Usage:
        /delete 3    -> Delete message #3 and all after it

    Requires confirmation before deleting.
    """
    if not args:
        print("Usage: /delete <message_index>")
        print("Show messages with: /list")
        return False

    try:
        index = int(args[0]) - 1  # Convert to 0-based
    except ValueError:
        print("Invalid message index")
        return False

    if index < 0 or index >= len(conversation["messages"]):
        print(f"Message index out of range (1-{len(conversation['messages'])})")
        return False

    # Show what will be deleted
    msg_count = len(conversation["messages"]) - index
    print(f"\nThis will delete {msg_count} message(s):")
    for i in range(index, len(conversation["messages"])):
        msg = conversation["messages"][i]
        content_preview = lines_to_text(msg["content"])[:60]
        print(f"  {i + 1}. [{msg['role']}] {content_preview}...")

    confirm = input("\nConfirm deletion? (y/n): ")

    if confirm.lower() == "y":
        deleted = delete_message_and_following(conversation, index)
        await save_conversation(session["conversation_path"], conversation)
        print(f"Deleted {deleted} message(s)")
    else:
        print("Deletion cancelled")

    return False
```

### Retry Command (Future Implementation)

**`/retry`** - Enter retry loop

This is a complex feature to implement later. Basic flow:
1. Capture current conversation state
2. Enter loop mode where messages are sent but not permanently saved
3. Try different prompts/AIs
4. Accept one result and commit, or cancel and revert

### Help Command

**`/help`** - Show available commands

```python
def cmd_help() -> bool:
    """Show help message."""
    print("""
PolyChat Commands:

AI Switching:
  /gpt, /gem, /cla, /grok, /perp, /mist, /deep
      Switch to specific AI provider

  /model [name]
      Show models or switch model

Conversation Management:
  /title [text]      Set or delete title
  /ai-title          Generate title with AI

  /summary [text]    Set or delete summary
  /ai-summary        Generate summary with AI

  /delete <index>    Delete message and all following
  /safe              Check for sensitive content

System:
  /help              Show this help
  /exit, /quit       Exit PolyChat

To send a message, just type without '/'.
Press Alt+Enter to send multiline messages.
""")
    return False
```


## Error Handling & Logging

### Error Strategy

**Principle**: Errors are logged (if `-l` specified) and displayed to user. API errors are also saved in conversation as "error" role messages.

### Logging Setup

```python
import logging
from pathlib import Path


def setup_logging(log_path: str, profile: dict) -> logging.Logger:
    """Setup error logging.

    Args:
        log_path: Path to log file (name only or full path)
        profile: Profile data (for log_dir mapping)

    Returns:
        Logger instance

    Only logs ERROR and WARNING levels.
    """
    # Map log path if needed
    if "/" not in log_path and "\\" not in log_path:
        # Name only - use log_dir from profile
        full_path = Path(profile["log_dir"]) / log_path
    else:
        # Full or relative path - map it
        full_path = Path(map_path(log_path, Path.cwd()))

    # Create directory
    full_path.parent.mkdir(parents=True, exist_ok=True)

    # Configure logger
    logger = logging.getLogger("polychat")
    logger.setLevel(logging.ERROR)

    # File handler
    handler = logging.FileHandler(full_path, encoding="utf-8")
    handler.setLevel(logging.ERROR)

    # Format
    formatter = logging.Formatter(
        "%(asctime)s.%(msecs)03dZ [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S"
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)

    return logger
```

### Error Types & Handling

**API Errors** (rate limits, auth failures, etc.):
```python
try:
    response = await provider.send_message(...)
except APIError as e:
    # Log it
    if logger:
        logger.error(
            f"API error: {e.provider} - {e.error_type} - {e}\n"
            f"Details: {e.details}"
        )

    # Add to conversation
    add_error_message(
        conversation,
        f"{e.error_type}: {e}",
        details={
            "provider": e.provider,
            "error_type": e.error_type,
            **e.details
        }
    )

    # Save conversation
    await save_conversation(conv_path, conversation)

    # Show user
    print(f"\nError: {e}")
```

**File I/O Errors**:
```python
try:
    await save_conversation(path, data)
except OSError as e:
    if logger:
        logger.error(f"Failed to save conversation: {path} - {e}")
    print(f"Error saving conversation: {e}")
```

**Profile/Key Loading Errors**:
```python
try:
    api_key = load_api_key(provider, config)
except ValueError as e:
    if logger:
        logger.error(f"API key loading failed: {provider} - {e}")
    print(f"Error: {e}")
    # Don't include key in error message
```

### What NOT to Log

- Successful API calls
- Model switches
- Profile loads
- Normal user actions

### What TO Log

- API errors (with full details)
- Exceptions (with traceback)
- File I/O failures
- Key loading failures

## Testing Strategy

### Unit Tests (No API Keys Required)

Use `pytest` with mocking for AI SDK calls.

**Example** (`tests/test_conversation.py`):
```python
import pytest
from poly_chat.conversation import (
    add_user_message,
    add_assistant_message,
    delete_message_and_following
)


def test_add_user_message():
    """Test adding user message."""
    conv = {"messages": []}

    add_user_message(conv, "Hello\nWorld")

    assert len(conv["messages"]) == 1
    assert conv["messages"][0]["role"] == "user"
    assert conv["messages"][0]["content"] == ["Hello", "World"]


def test_delete_message_and_following():
    """Test time travel deletion."""
    conv = {"messages": [
        {"role": "user", "content": ["msg1"]},
        {"role": "assistant", "content": ["msg2"]},
        {"role": "user", "content": ["msg3"]},
        {"role": "assistant", "content": ["msg4"]}
    ]}

    deleted = delete_message_and_following(conv, 2)

    assert deleted == 2
    assert len(conv["messages"]) == 2
```

**Example** (`tests/test_ai/test_providers.py`):
```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from poly_chat.ai.openai_provider import OpenAIProvider


@pytest.mark.asyncio
async def test_openai_streaming(monkeypatch):
    """Test OpenAI streaming with mocked API."""

    # Mock OpenAI client
    mock_client = AsyncMock()
    mock_stream = AsyncMock()

    # Mock chunks
    async def mock_stream_iter():
        for chunk in ["Hello", " ", "World"]:
            mock_chunk = MagicMock()
            mock_chunk.choices = [MagicMock()]
            mock_chunk.choices[0].delta.content = chunk
            yield mock_chunk

    mock_stream.__aiter__ = mock_stream_iter

    mock_client.chat.completions.create.return_value = mock_stream

    # Inject mock
    provider = OpenAIProvider("fake-key")
    provider.client = mock_client

    # Test
    messages = [{"role": "user", "content": ["Test"]}]
    chunks = []

    async for chunk in provider.send_message_streaming(messages, "gpt-4"):
        chunks.append(chunk)

    assert chunks == ["Hello", " ", "World"]
```

### Integration Tests (Optional, Require API Keys)

```python
# tests/test_integration.py

import pytest
import os

# Skip if API keys not available
requires_api_keys = pytest.mark.skipif(
    "OPENAI_API_KEY" not in os.environ,
    reason="API keys not configured"
)


@pytest.mark.asyncio
@requires_api_keys
async def test_real_openai_call():
    """Test actual OpenAI API call (optional)."""
    from poly_chat.ai.openai_provider import OpenAIProvider

    api_key = os.environ["OPENAI_API_KEY"]
    provider = OpenAIProvider(api_key)

    messages = [{"role": "user", "content": ["Say hello"]}]

    response, usage = await provider.send_message(
        messages,
        "gpt-4o-mini"  # Use cheap model for tests
    )

    assert isinstance(response, str)
    assert len(response) > 0
    assert usage.total_tokens > 0
```

### Test Fixtures

```python
# tests/conftest.py

import pytest
from pathlib import Path
import tempfile


@pytest.fixture
def temp_profile(tmp_path):
    """Create temporary profile for testing."""
    profile = {
        "default_ai": "openai",
        "models": {
            "openai": "gpt-4",
            "claude": "claude-sonnet-4"
        },
        "conversations_dir": str(tmp_path / "convs"),
        "log_dir": str(tmp_path / "logs"),
        "api_keys": {
            "openai": {
                "type": "env",
                "key": "OPENAI_API_KEY"
            }
        }
    }
    return profile


@pytest.fixture
def empty_conversation():
    """Create empty conversation for testing."""
    return {
        "metadata": {
            "title": None,
            "summary": None,
            "system_prompt_key": None,
            "default_model": None,
            "created_at": None,
            "updated_at": None
        },
        "messages": []
    }
```

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=poly_chat

# Run only unit tests (skip integration)
poetry run pytest -m "not integration"

# Run specific test file
poetry run pytest tests/test_conversation.py

# Verbose output
poetry run pytest -v
```

## Implementation Order

### Phase 1: Foundation

1. **Project setup**
   - Create folder structure
   - `pyproject.toml` with dependencies
   - `__init__.py`, `__main__.py`

2. **profile.py**
   - Path mapping (`map_path`)
   - Profile loading (`load_profile`)
   - Profile creation (`create_profile`)
   - Validation

3. **message_formatter.py**
   - Text to lines conversion
   - Trimming algorithm
   - Lines to text conversion

4. **Test Phase 1**
   - Unit tests for profile loading
   - Unit tests for message formatting

### Phase 2: Conversation & Keys

5. **conversation.py**
   - Load/save conversation
   - Add user/assistant/error messages
   - Delete messages (time travel)
   - Update metadata

6. **keys/loader.py** and submodules
   - Unified interface
   - Environment variable loading
   - Keychain access (macOS)
   - JSON file loading

7. **Test Phase 2**
   - Conversation operations
   - Key loading (mocked)

### Phase 3: AI Providers

8. **ai/base.py**
   - Protocol definition
   - Error classes
   - Token usage dataclass

9. **ai/openai_provider.py**
   - Streaming and non-streaming
   - Message formatting
   - Cost calculation

10. **ai/claude_provider.py**
    - Same structure as OpenAI

11. **Test Phase 3**
    - Mock AI provider calls
    - Test message formatting
    - Test error handling

### Phase 4: Streaming & Commands

12. **streaming.py**
    - Display streaming responses
    - Handle Ctrl-C during stream
    - Accumulate full response

13. **models.py**
    - Model registry
    - Provider detection

14. **commands.py**
    - Command parsing
    - All command implementations
    - Error handling

15. **Test Phase 4**
    - Command parsing
    - Command execution (mocked providers)

### Phase 5: CLI & REPL

16. **cli.py**
    - Argument parsing
    - REPL loop with `prompt_toolkit`
    - Session management
    - Startup/shutdown flow

17. **Logging setup**
    - Error-only logging
    - File path mapping

18. **Test Phase 5**
    - End-to-end flow (mocked)

### Phase 6: Additional Providers

19. **ai/gemini_provider.py**
20. **ai/grok_provider.py**
21. **ai/perplexity_provider.py**
22. **ai/mistral_provider.py**
23. **ai/deepseek_provider.py**

Each provider:
- Implement streaming/non-streaming
- Format messages correctly
- Calculate costs
- Test with mocks

### Phase 7: Polish & Testing

24. **Integration tests** (optional, with real API keys)
25. **Documentation** updates
26. **README.md** with examples
27. **System prompts** (default, critic, helpful, etc.)

## Edge Cases & Examples

### Edge Case: Empty Conversation

**Scenario**: User starts new conversation, immediately saves.

**Expected**:
- Empty messages array
- Metadata all `null`
- File created successfully
- No errors

### Edge Case: Very Long Conversation

**Scenario**: 1000+ messages, total 500KB.

**Expected**:
- Load/save works (async I/O handles it)
- Streaming response still works
- Cost might be high (show warning?)

### Edge Case: API Key in Multiple Places

**Scenario**: API key in env var AND keychain.

**Expected**:
- Use first configured method in profile
- No fallback (explicit configuration)

### Edge Case: Malformed JSON in Conversation File

**Scenario**: User manually edits file, breaks JSON.

**Expected**:
- Clear error message
- Point to file and line number
- Suggest restoring from git

### Edge Case: Network Failure Mid-Stream

**Scenario**: Internet drops during streaming response.

**Expected**:
- API raises exception
- Catch it, add error message to conversation
- Save conversation with partial response + error
- User can retry

### Edge Case: System Prompt File Deleted

**Scenario**: Conversation references `@/system-prompts/critic.txt`, file deleted.

**Expected**:
- Error when loading system prompt
- Show clear message
- Conversation still usable (just without system prompt)

### Example Session

```
$ pc -p ~/my-profile.json

No conversation specified.
Options:
  1. Create new conversation
  2. Open existing conversation
  3. Exit

Choice (1-3): 1

Conversation name (Enter for auto-generated): strategy-2026

Created: /Users/you/poly-chat-logs/strategy-2026.json

PolyChat - /Users/you/poly-chat-logs/strategy-2026.json
AI: claude (claude-sonnet-4)
Messages: 0

Type your message (Alt+Enter to send, /help for commands)

You: What are the key factors in market expansion?

CLAUDE (claude-sonnet-4):

Here are the main factors to consider when expanding into new markets:

1. **Market Research**
   - Understand local demand and customer needs
   - Analyze competition and market saturation
   - Identify cultural and regulatory differences

2. **Financial Planning**
   - Calculate entry costs and ROI projections
   - Assess currency risks and tax implications
   - Secure adequate funding

3. **Strategic Partnerships**
   - Find local partners who understand the market
   - Build distribution channels
   - Leverage existing networks

Would you like me to elaborate on any of these areas?

You: /title Market Expansion Strategy

Title set to: Market Expansion Strategy

You: /ai-summary

Generating summary...

Suggested summary: Discussion of key factors for market expansion including research, financial planning, and partnerships.

Accept? (y/n/e to edit): y

Summary set

You: /safe

Checking conversation for sensitive content...

No PII, credentials, or unsafe content found. The conversation discusses general business strategy concepts without revealing any sensitive information.

[Safety check complete - not saved to conversation]

You: /exit

Conversation saved. Goodbye!
```

---

## Notes for Implementation

1. **Start simple**: Get basic conversation flow working first, add features incrementally
2. **Test continuously**: Write tests as you go, not at the end
3. **Use official SDKs**: Don't reinvent API calls, learn each SDK properly
4. **Async everywhere**: Network I/O is async, embrace it
5. **Error messages matter**: Users should never be confused about what went wrong
6. **Git-friendly JSON**: Pretty print, ensure UTF-8, use line arrays
7. **Security first**: Never log/display API keys
8. **Keep it focused**: Resist scope creep, stick to conversation management

## Future Enhancements (Out of Scope for v1)

- Retry loop (complex state management)
- Conversation search/filtering
- Token counting before sending
- Context window compression/summarization
- Multiple system prompts per conversation
- Conversation export to markdown
- Keyboard shortcuts for commands
- Conversation templates
- Message editing (not just deletion)
- Custom AI provider plugins

Focus on getting v1 working: load, send, receive, save, basic commands. Ship it. Use it. Iterate.
