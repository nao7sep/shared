# PolyChat

Multi-AI CLI chat tool for long-term, version-controlled chats.

## Overview

PolyChat is a command-line chat interface that supports multiple AI providers (OpenAI, Claude, Gemini, Grok, Perplexity, Mistral, DeepSeek). Unlike code-focused AI tools, PolyChat is designed for thoughtful, long-term chats with git-version-controlled chat history.

## Features

- **Multiple AI Providers**: Switch seamlessly between OpenAI GPT, Claude, Gemini, and more
- **Git-Friendly Logs**: Chat history stored as formatted JSON with messages as line arrays
- **Retry & Time Travel**: Re-ask questions without deleting history, or delete messages to "go back in time"
- **Secure API Keys**: Support for environment variables, macOS Keychain, and JSON files
- **System Prompts**: Predefined and custom system prompts with version control
- **Streaming Responses**: Real-time response display with async streaming
- **Profile-Based**: Each profile contains AI preferences, API keys, and default settings

## Installation

```bash
cd poly-chat
poetry install
```

## Quick Start

### 1. Create a Profile

```bash
poetry run pc init ~/my-profile.json
```

This interactive wizard will guide you through:
- Selecting default AI provider
- Configuring API keys (environment variables, Keychain, or JSON file)
- Setting chat history and error log directories
- Choosing a default system prompt

### 2. Start a Chat

```bash
# With existing chat
poetry run pc -p ~/my-profile.json -c ~/chats/my-chat.json

# Or let it prompt you for chat history file
poetry run pc -p ~/my-profile.json
```

### 3. Chat

```
You: What are the key considerations for expanding into Asian markets?

Claude: Here are the main factors to consider:

1. Market Research
   - Cultural differences...
```

## Usage

### Basic Commands

```bash
# Create new profile
pc init <profile-path>

# Start with profile
pc -p <profile-path>

# Start with specific chat
pc -p <profile-path> -c <chat-path>

# Enable error logging
pc -p <profile-path> -l debug.log
```

### In-Chat Commands

**Provider Shortcuts:**
- `/gpt` - Switch to OpenAI GPT
- `/gem` - Switch to Google Gemini
- `/cla` - Switch to Anthropic Claude
- `/grok` - Switch to xAI Grok
- `/perp` - Switch to Perplexity
- `/mist` - Switch to Mistral
- `/deep` - Switch to DeepSeek

**Model Management:**
- `/model` - Show available models for current provider
- `/model <name>` - Switch to specified model

**Chat Control:**
- `/retry` - Replace last response (retry mode)
- `/delete <index>` - Delete message and all following
- `/delete last` - Delete last message

**Metadata:**
- `/title <text>` - Set chat title
- `/summary <text>` - Set chat summary

**Other:**
- `/help` - Show all commands
- `/exit` or `/quit` - Exit PolyChat

## Configuration

### Profile File Format

```json
{
  "default_ai": "claude",
  "models": {
    "openai": "gpt-5-mini",
    "claude": "claude-haiku-4-5",
    "gemini": "gemini-3-flash-preview"
  },
  "system_prompt": "@/system-prompts/default.txt",
  "chats_dir": "~/poly-chat-logs",
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

### Path Mapping

- `~` or `~/...` → User home directory
- `@` or `@/...` → App root directory (where pyproject.toml is)
- Absolute paths → Used as-is
- Relative paths without prefix → **Error** (to avoid ambiguity)

### API Key Configuration

**Environment Variables:**
```json
{
  "type": "env",
  "key": "OPENAI_API_KEY"
}
```

**macOS Keychain:**
```json
{
  "type": "keychain",
  "service": "poly-chat",
  "account": "claude-api-key"
}
```

**JSON File:**
```json
{
  "type": "json",
  "path": "~/.secrets/api-keys.json",
  "key": "gemini"
}
```

### System Prompts

System prompts are stored in `system-prompts/` directory. Built-in prompts:
- `default.txt` - Balanced, helpful assistant
- `critic.txt` - Critical thinking, challenges assumptions
- `helpful.txt` - Warm, encouraging tone
- `concise.txt` - Brief, to-the-point responses

You can create custom prompts and reference them:
```json
{
  "system_prompt": "@/system-prompts/my-custom-prompt.txt"
}
```

## Chat History Format

Chat history files are stored as JSON with git-friendly formatting:

```json
{
  "metadata": {
    "title": "Business Strategy 2026",
    "summary": "Long-term planning discussion",
    "system_prompt_key": "@/system-prompts/default.txt",
    "created_at": "2026-02-02T10:00:00.123456Z",
    "updated_at": "2026-02-02T15:30:45.789012Z"
  },
  "messages": [
    {
      "role": "user",
      "content": [
        "I'm planning to expand our business into Asian markets.",
        "",
        "What are the key considerations I should focus on?"
      ],
      "timestamp": "2026-02-02T10:00:00.123456Z"
    },
    {
      "role": "assistant",
      "content": [
        "Here are the main factors:",
        "",
        "1. Market Research",
        "2. Regulatory Environment"
      ],
      "timestamp": "2026-02-02T10:00:05.789012Z",
      "model": "claude-haiku-4-5"
    }
  ]
}
```

Messages are stored as line arrays for better git diffs and readability.

## Development

### Running Tests

```bash
poetry run pytest
```

### Code Formatting

```bash
poetry run black .
poetry run ruff check .
```

### Type Checking

```bash
poetry run mypy src/poly_chat
```

## Architecture

- `profile.py` - Profile management and path mapping
- `chat.py` - Chat history data management
- `message_formatter.py` - Line array formatting
- `keys/` - API key management (env vars, Keychain, JSON)
- `ai/` - AI provider implementations
- `models.py` - Model registry and provider mapping
- `commands.py` - Command system
- `streaming.py` - Streaming response handling
- `cli.py` - REPL loop and main entry point

## License

See LICENSE file for details.

## Contributing

Contributions welcome! Please follow the existing code style and add tests for new features.
