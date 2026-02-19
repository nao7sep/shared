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
- **Centralized Runtime Policy**: Optional per-provider output limits and shared timeout policy

## Installation

```bash
cd polychat
uv sync
```

## Quick Start

### 1. Create a Profile

```bash
uv run pc init ~/my-profile.json
```

This creates a template file:
- Profile JSON at the path you provide

The generated profile template uses home-based paths (`~/polychat/...`) for directories and app root paths (`@/prompts/...`) for built-in prompt files.
It also includes mixed API-key configuration examples (`env`, `keychain`, `json`) so you can pick the style you want.
Then edit the template values (models, paths, and `api_keys`) before running PolyChat.

### 2. Start PolyChat

```bash
# Start with a specific chat
uv run pc -p ~/my-profile.json -c ~/chats/my-chat.json

# Or start without a chat (use /new or /open commands)
uv run pc -p ~/my-profile.json
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

If `-l/--log` is omitted, PolyChat creates one log file for the current app run in the profile's `logs_dir`:
- `polychat_YYYY-MM-DD_HH-MM-SS.log`

Logs are written in a structured plaintext block format and include contextual events such as app/session start and stop, command execution, chat lifecycle actions, and AI request/response/error details.

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
- `/model <query>` - Switch model via exact or fuzzy match (provider auto-detected)
- `/model default` - Restore profile default AI and model
- `/helper` - Show current helper AI model
- `/helper <query>` - Set helper AI model via exact or fuzzy match
- `/helper <shortcut>` - Set helper from provider shortcut (`gpt`, `gem`, `cla`, `grok`, `perp`, `mist`, `deep`)
- `/helper default` - Restore helper AI from profile default

**Configuration:**
- `/input` - Show current input mode
- `/input quick` - Enter sends, Option/Alt+Enter inserts newline
- `/input compose` - Enter inserts newline, Option/Alt+Enter sends
- `/input default` - Restore profile default input mode
- `/timeout` - Show current timeout setting
- `/timeout default` - Restore profile default timeout
- `/timeout <secs>` - Set timeout (0 = wait forever)
- `/system` - Show current system prompt path
- `/system --` - Remove system prompt from chat
- `/system default` - Restore profile default system prompt
- `/system <persona>` - Set system prompt by persona (e.g., `razor`, `socrates`)
- `/system <path>` - Set system prompt by path

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

**What "Last Interaction" Means:**
PolyChat defines the "last interaction" as one of:
1. A trailing `user + assistant` pair
2. A trailing `user + error` pair
3. A standalone trailing `error`

`/retry` retries the last interaction. `/rewind` and `/rewind last` delete the last interaction.

**Chat Control:**
- `/retry` - Retry the last interaction and generate candidate responses
- `/apply` - Apply latest retry candidate and exit retry mode
- `/apply last` - Apply latest retry candidate and exit retry mode
- `/apply <hex_id>` - Apply one retry candidate by ID and exit retry mode
- `/cancel` - Abort retry and keep original response
- `/secret` - Show current secret mode state
- `/secret on/off` - Explicitly enable/disable secret mode
- `/search` - Show current search mode state and supported providers
- `/search on/off` - Enable/disable web search with inline citations
- `/rewind` - Delete last full interaction (user+assistant/user+error), or trailing error
- `/rewind last` - Delete the last full interaction (user+assistant/user+error), or trailing error
- `/rewind <hex_id>` - Delete that message and all following messages
- `/purge <hex_id> [hex_id2 ...]` - Delete specific messages (breaks context)

**History:**
- `/history` - Show last 10 messages
- `/history all` - Show all messages
- `/history errors` - Show error messages only
- `/history <n>` - Show last n messages
- `/show <hex_id>` - Show full content of one message
- `/status` - Show current profile/chat/session status

**Metadata:**
- `/title` - Generate title using AI
- `/title --` - Clear title
- `/title <text>` - Set chat title
- `/summary` - Generate summary using AI
- `/summary --` - Clear summary
- `/summary <text>` - Set chat summary

**Safety:**
- `/safe` - Check entire chat for unsafe content
- `/safe <hex_id>` - Check one message for unsafe content

**Other:**
- `/help` - Show all commands
- `/exit` or `/quit` - Exit PolyChat

When commands show chat lists for selection (`/open`, `/switch`, `/rename`, `/delete`), "Last Updated" is shown in your local time.
For `/model` and `/helper`, fuzzy matching normalizes names to alphanumeric characters and uses in-order subsequence matching (for example, `op4` or `o4.6` can match `claude-opus-4-6`). When multiple models match, PolyChat prompts you to choose by number.

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
When search is enabled, AI responses include a "Sources:" section with citation titles and URLs reported by the provider. Citation records saved in chat history store only `number`, `title`, and `url` (with `null` for unavailable/invalid values).

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
  "system_prompt": "@/prompts/system/default.txt",
  "title_prompt": "@/prompts/title.txt",
  "summary_prompt": "@/prompts/summary.txt",
  "safety_prompt": "@/prompts/safety.txt",
  "chats_dir": "~/polychat/chats",
  "logs_dir": "~/polychat/logs",
  "api_keys": {
    "openai": {
      "type": "env",
      "key": "OPENAI_API_KEY"
    },
    "claude": {
      "type": "keychain",
      "service": "polychat",
      "account": "claude-api-key"
    },
    "gemini": {
      "type": "json",
      "path": "~/.secrets/api-keys.json",
      "key": "gemini"
    }
  },
  "ai_limits": {
    "default": {
      "max_output_tokens": null,
      "search_max_output_tokens": null
    },
    "providers": {
      "claude": {
        "max_output_tokens": null,
        "search_max_output_tokens": null
      }
    },
    "helper": {
      "max_output_tokens": null,
      "search_max_output_tokens": null
    }
  }
}
```

### Required Directories

The profile requires two directory paths:

**`chats_dir`** - Where conversation history files are stored
- Chat files are JSON format with `.json` extension
- Named by user or auto-generated with timestamps
- Use `/new`, `/open`, `/switch`, `/rename`, and `/delete` commands to manage

**`logs_dir`** - Where application log files are written
- One log file per app run: `polychat_YYYY-MM-DD_HH-MM-SS.log`
- Structured plaintext format with contextual events
- Includes AI requests/responses, commands, errors


Both directories are created automatically if they don't exist.

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
  "service": "polychat",
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

### Path Mapping

PolyChat supports special path prefixes for portability across platforms:

**`~` or `~/...`** → User home directory
- macOS/Linux: `/Users/username/` or `/home/username/`
- Windows: `C:\Users\YourName\`
- Example: `~/polychat/chats/` → `/Users/username/polychat/chats/`

**`@` or `@/...`** → App root directory
- Points to the installed `polychat` package directory
- Example: `@/prompts/title.txt` → `/path/to/site-packages/polychat/prompts/title.txt`
- Useful for accessing bundled prompts and resources

**Absolute paths** → Used as-is
- Example: `/usr/local/polychat/` or `C:\Program Files\polychat\`

**Relative paths without prefix** → **Error** (rejected to avoid ambiguity)

### Prompts and Customization

PolyChat uses file-based prompts for all AI interactions. Prompts are configured in your profile and can be customized by pointing to different files.

#### Built-in Prompts

Built-in prompts are bundled in `src/polychat/prompts/` (installed as `polychat/prompts/`):

**System Prompts** (`prompts/system/`):
- `default.txt` - Balanced, helpful assistant
- `socrates.txt` - Socratic questioning, teaches through inquiry
- `spark.txt` - Creative brainstorming, energetic ideation
- `razor.txt` - Ultra-concise, direct answers
- `devil.txt` - Devil's advocate, challenges assumptions
- `strategist.txt` - Strategic planning, systems thinking
- `scholar.txt` - Comprehensive research, authoritative depth

See `src/polychat/prompts/system/README.md` for detailed persona descriptions.

**Helper Prompts** (`prompts/`):
- `title.txt` - Chat title generation template (uses `{CONTEXT}` placeholder)
- `summary.txt` - Chat summary generation template (uses `{CONTEXT}` placeholder)
- `safety.txt` - Safety check template (uses `{CONTENT}` placeholder)

#### Profile Configuration

All prompts are configured in your profile as file paths:

```json
{
  "system_prompt": "@/prompts/system/default.txt",
  "title_prompt": "@/prompts/title.txt",
  "summary_prompt": "@/prompts/summary.txt",
  "safety_prompt": "@/prompts/safety.txt"
}
```

#### Customization

To customize prompts:

1. Copy a prompt file to a location of your choice
2. Edit the content as needed
3. Update your profile to point to the custom file:

```json
{
  "system_prompt": "~/my-prompts/custom-system.txt",
  "title_prompt": "~/my-prompts/custom-title.txt"
}
```

**Template placeholders:**
- `{CONTEXT}` - Replaced with conversation context (title/summary prompts)
- `{CONTENT}` - Replaced with content to analyze (safety prompt)

Changes to prompt files take effect immediately for new messages (no restart needed).

### AI Request Limits (Optional)

`ai_limits` lets you control output token budgets centrally.

- Precedence:
  - `ai_limits.default`
  - `ai_limits.providers.<provider>`
  - `ai_limits.helper` (helper-only requests like `/title`, `/summary`, `/safe`)
- Allowed keys:
  - `max_output_tokens`
  - `search_max_output_tokens`
- Values must be positive integers or `null`.
- `null` means "leave that limit unset in profile config."
- `search_max_output_tokens` is used when `/search` is ON; otherwise `max_output_tokens` is used.
- Limits are applied for normal assistant requests and helper requests (`/title`, `/summary`, `/safe`).
- Claude requires `max_tokens`; when resolved `max_output_tokens` is unset, PolyChat applies a fallback default of `4096`.

### Timeout Behavior

- `timeout` in profile (or `/timeout`) is the base read timeout in seconds.
- Base timeout is applied to AI provider `read` timeout.
- When `/search` is ON, AI provider read timeout is automatically multiplied by `3`.
- `0` means no timeout (wait forever).

## Chat History Format

Chat history files are stored as JSON with git-friendly formatting:

```json
{
  "metadata": {
    "title": "Business Strategy 2026",
    "summary": "Long-term planning discussion",
    "system_prompt": "@/prompts/system/default.txt",
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

## License

See LICENSE file for details.

## Contributing

Contributions welcome! Please follow the existing code style and add tests for new features.

## Development

### Running Tests

```bash
uv run pytest
```

### Code Formatting

```bash
uv run ruff check .
uv run ruff format .
```

### Type Checking

```bash
uv run mypy src/polychat
```
