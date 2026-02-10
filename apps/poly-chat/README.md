# PolyChat

Multi-AI CLI chat tool for long-term, version-controlled chats.

## Overview

PolyChat is a command-line chat interface that supports multiple AI providers (OpenAI, Claude, Gemini, Grok, Perplexity, Mistral, DeepSeek). Unlike code-focused AI tools, PolyChat is designed for thoughtful, long-term chats with git-version-controlled chat history.

## Features

- **Multiple AI Providers**: Switch seamlessly between OpenAI GPT, Claude, Gemini, and more
- **Web Search**: Enable AI-powered web search with inline citations (OpenAI, Claude, Gemini, Grok, Perplexity)
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

This creates template files:
- Profile JSON at the path you provide

The generated profile template uses home-based paths (`~/poly-chat/...`) and an inline default system prompt (no `@/...` paths), which is safer for Windows and one-file packaging.
It also includes mixed API-key configuration examples (`env`, `keychain`, `json`, `direct`) so you can pick the style you want.
Then edit the template values (models, paths, and `api_keys`) before running PolyChat.

### 2. Start PolyChat

```bash
# Start with a specific chat
poetry run pc -p ~/my-profile.json -c ~/chats/my-chat.json

# Or start without a chat (use /new or /open commands)
poetry run pc -p ~/my-profile.json
```

The app goes straight to the REPL and shows configured AI providers.

### 3. Chat

Messages are multiline:
- Default input mode is **quick**:
  - **Enter** sends
  - **Option+Enter** (Alt+Enter) inserts a new line
- In **compose** mode:
  - **Enter** inserts a new line
  - **Option+Enter** (Alt+Enter) sends
- `Ctrl+Enter` may work in some terminals if it is sent as `Ctrl+J` (send in both modes)

Use `/input quick` or `/input compose` to switch behavior.

```
What are the key considerations for
expanding into Asian markets?
[Enter to send in quick mode]

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

CLI path flags use the same path mapping rules:
- `-p/--profile` (profile path)
- `-c/--chat` (chat history path)
- `-l/--log` (error log path)

Use `~/...`, `@/...`, or absolute paths. Plain relative paths are rejected.

If `-l/--log` is omitted, PolyChat creates one log file for the current app run in the profile's `log_dir`:
- `poly-chat_YYYY-MM-DD_HH-MM-SS.log`

Logs are written in a structured plaintext block format and include contextual events such as app/session start and stop, command execution, chat lifecycle actions, and AI request/response/error details (with redaction for sensitive token patterns).

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
- `/model default` - Restore profile default AI and model
- `/helper` - Show current helper AI model
- `/helper <model>` - Set helper AI model
- `/helper default` - Restore helper AI from profile default

**Chat File Management:**
- `/new` - Create new chat with timestamped filename
- `/new <name>` - Create new chat with the provided name
- `/open` - Select from list of chats
- `/open <path>` - Open specific chat file
- `/switch` - Switch chats (save current, then select chat to open)
- `/switch <path>` - Switch to specific chat file
- `/close` - Close current chat
- `/rename` - Select chat to rename
- `/rename current <new-name>` - Rename current chat
- `/rename <chat> <new-name>` - Rename specific chat by name/path
- `/delete` - Select chat to delete
- `/delete current` - Delete current chat
- `/delete <path>` - Delete specific chat file

Delete operations always ask for confirmation and require typing `yes`.

**Chat Control:**
- `/retry` - Enter retry mode and generate candidate responses
- `/apply <hex_id>` - Apply one retry candidate and exit retry mode
- `/cancel` - Abort retry and keep original response
- `/secret` - Show current secret mode state
- `/secret on|off` - Explicitly enable/disable secret mode
- `/search` - Show current search mode state and supported providers
- `/search on|off` - Enable/disable web search with inline citations
- `/rewind <hex_id>` - Delete that message and all following messages
- `/rewind turn` - Delete the last full interaction (user+assistant/error)
- `/rewind last` - Delete only the last message
- `/purge <hex_id> [hex_id2 ...]` - Delete specific messages (breaks context)

**History:**
- `/history` - Show last 10 messages
- `/history <n>` - Show last n messages
- `/history all` - Show all messages
- `/history --errors` - Show error messages only
- `/show <hex_id>` - Show full content of one message
- `/status` - Show current profile/chat/session status

**Metadata:**
- `/title` - Generate title using AI
- `/title <text>` - Set chat title
- `/title --` - Clear title
- `/summary` - Generate summary using AI
- `/summary <text>` - Set chat summary
- `/summary --` - Clear summary

**Safety:**
- `/safe` - Check entire chat for unsafe content
- `/safe <hex_id>` - Check one message for unsafe content

**Configuration:**
- `/input` - Show current input mode
- `/input quick` - Enter sends, Option/Alt+Enter inserts newline
- `/input compose` - Enter inserts newline, Option/Alt+Enter sends
- `/input default` - Restore profile default input mode
- `/timeout` - Show current timeout setting
- `/timeout <secs>` - Set timeout (0 = wait forever)
- `/timeout default` - Restore profile default timeout
- `/system` - Show current system prompt
- `/system <path>` - Set system prompt path
- `/system --` - Remove system prompt from chat
- `/system default` - Restore profile default system prompt

**Other:**
- `/help` - Show all commands
- `/exit` or `/quit` - Exit PolyChat

When commands show chat lists for selection (`/open`, `/switch`, `/rename`, `/delete`), "Last Updated" is shown in your local time.

### Web Search

PolyChat supports AI-powered web search with inline citations for select providers. When search mode is enabled, the AI can access current information from the web and provide citations for its responses.

**Supported Providers:**
- OpenAI (GPT models)
- Claude (Anthropic)
- Gemini (Google)
- Grok (xAI)
- Perplexity (Sonar models)

**Not Supported:**
- Mistral (requires different Agents API)
- DeepSeek (no search API available)

**Usage:**
```bash
# Enable persistent search mode
/search on

# Send messages with web search enabled
What are the latest developments in AI?
Where can I find current stock prices for AAPL?

# Disable search mode
/search off

# Check current mode
/search
```

**Citations:**
When search is enabled, AI responses will include a "Sources:" section at the end listing the URLs and titles of web pages used to generate the response.

**Mode Combinations:**
Search mode can be combined with secret mode:
- `/secret on` + `/search on` - All messages use both secret and search

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
  "timeout": 30,
  "input_mode": "quick",
  "system_prompt": {
    "type": "text",
    "content": "You are a helpful assistant."
  },
  "chats_dir": "~/poly-chat/chats",
  "log_dir": "~/poly-chat/logs",
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

You can also use inline prompt text in profile JSON:
```json
{
  "system_prompt": {
    "type": "text",
    "content": "You are a helpful assistant."
  }
}
```

You can create custom prompts and reference them:
```json
{
  "system_prompt": "@/system-prompts/my-custom-prompt.txt"
}
```

## Windows & One-File Packaging Notes

These are practical notes if you package PolyChat as a single-file Windows executable:

- Profile templates generated by `pc init` avoid `@/...` paths by default.
- `@/...` paths are still supported in source/dev usage, but can be unreliable in one-file packaged mode.
- Keep profile paths explicit (`~/...` or absolute paths) when packaging.
- Use `env` or `json` API-key modes for predictable cross-platform behavior; Keychain config is macOS-specific.
- Terminal key behavior can differ by host (for example `Alt+Enter` handling), so verify in your target Windows terminal.

## Chat History Format

Chat history files are stored as JSON with git-friendly formatting:

```json
{
  "metadata": {
    "title": "Business Strategy 2026",
    "summary": "Long-term planning discussion",
    "system_prompt": "@/system-prompts/default.txt",
    "created_at": "2026-02-02T10:00:00.123456Z",
    "updated_at": "2026-02-02T15:30:45.789012Z"
  },
  "messages": [
    {
      "timestamp": "2026-02-02T10:00:00.123456Z",
      "role": "user",
      "content": [
        "I'm planning to expand our business into Asian markets.",
        "",
        "What are the key considerations I should focus on?"
      ]
    },
    {
      "timestamp": "2026-02-02T10:00:05.789012Z",
      "role": "assistant",
      "model": "claude-haiku-4-5",
      "content": [
        "Here are the main factors:",
        "",
        "1. Market Research",
        "2. Regulatory Environment"
      ]
    }
  ]
}
```

Note: `system_prompt` is used in both profile and chat history metadata.

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
- `session_manager.py` - Unified runtime session state, timeout/cache control
- `chat.py` - Chat history data management
- `message_formatter.py` - Line array formatting
- `keys/` - API key management (env vars, Keychain, JSON)
- `ai/` - AI provider implementations
- `models.py` - Model registry and provider mapping
- `commands/` - Command handler and command mixins
- `streaming.py` - Streaming response handling
- `repl.py` - Interactive REPL loop
- `orchestrator.py` - Chat flow orchestration and persistence decisions
- `cli.py` - CLI bootstrap and app startup

## License

See LICENSE file for details.

## Contributing

Contributions welcome! Please follow the existing code style and add tests for new features.
