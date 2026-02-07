# PolyChat Refactoring Plan - February 2026

## Overview

This document outlines a comprehensive refactoring of PolyChat to add new features, fix bugs, and improve the overall architecture. The refactoring is organized into logical segments that can be implemented incrementally.

---

## Table of Contents

1. [System Prompt Refactoring](#1-system-prompt-refactoring)
2. [Secret Mode](#2-secret-mode)
3. [Delete Suffix Support (`--`)](#3-delete-suffix-support---)
4. [Safe Command Implementation](#4-safe-command-implementation)
5. [Helper AI Model](#5-helper-ai-model)
6. [Revert to Default Values](#6-revert-to-default-values)
7. [Retry Command Fix](#7-retry-command-fix)
8. [Purge Command](#8-purge-command)
9. [History/Show Commands](#9-historyshow-commands)
10. [Smart Context Architecture](#10-smart-context-architecture)
11. [Hex ID System](#11-hex-id-system)
12. [Miscellaneous](#12-miscellaneous)

---

## 1. System Prompt Refactoring

### Current State

- Uses `system_prompt_key` identifier throughout the codebase
- Stored in chat metadata as `system_prompt_key`
- Always represents a file path containing system prompt text

### Changes Required

#### 1.1 Rename Identifiers

| Current Name | New Name | Description |
|--------------|----------|-------------|
| `system_prompt_key` | `system_prompt_path` | The original path string (as stored in profile or provided by user) |
| (new) | `system_prompt_mapped_path` | The resolved absolute path used for file reading |

**Files to modify:**
- `src/poly_chat/chat.py` - metadata field name
- `src/poly_chat/cli.py` - variable names, session state
- `src/poly_chat/commands.py` - command handling
- `src/poly_chat/profile.py` - profile loading
- Tests files

#### 1.2 Path Storage Rules

When saving `system_prompt_path` to chat history:
- If path starts with `~` or `@` → save as-is (portable)
- If path is absolute → save as-is (user has a reason)
- If path is relative → save as-is (will be resolved at load time)

**Important:** Never normalize paths. Store exactly what user provides.

#### 1.3 New `/system` Command

```
/system <path>      Set system prompt path for current chat session
/system --          Remove system prompt from current chat session
/system default     Restore to profile's default system prompt
/system             Show current system prompt path
```

**Path mapping rules for `/system <path>`:**
- `~` or `~/...` → Maps to home directory
- `@` or `@/...` → Maps to app root directory
- Absolute paths → Used as-is
- Relative paths without prefix → **ERROR** (security/ambiguity)
- **Never map to current directory** (security vulnerability)

**Implementation notes:**
- Store the original path in `system_prompt_path` metadata
- Compute `system_prompt_mapped_path` at runtime for file reading
- Update session state immediately when command is executed

#### 1.4 Chat History Metadata Update

```json
{
  "metadata": {
    "title": "...",
    "summary": "...",
    "system_prompt_path": "@/system-prompts/default.txt",
    "default_model": "claude-haiku-4-5",
    "created_at": "...",
    "updated_at": "..."
  }
}
```

### Tasks

- [ ] Rename `system_prompt_key` to `system_prompt_path` in all files
- [ ] Add `system_prompt_mapped_path` computation in `profile.py`
- [ ] Implement `/system` command with all variants
- [ ] Update chat metadata structure
- [ ] Add path validation (reject unmapped relative paths)
- [ ] Update tests

---

## 2. Secret Mode

### Description

Secret mode allows users to ask questions without affecting chat history (both file and RAM). Useful for:
- "Did I talk about this?" without revealing details
- "What else should I add for better context?"
- Any question user doesn't want logged

### Behavior

- **One-shot feature**: Each secret question is independent
- **No continuous interaction**: Even if user asks 100 questions in secret mode, each only sees messages from before secret mode was initiated
- **Nothing saved**: Neither user message nor AI response is saved to file or RAM
- **Toggle support**: Can be turned on/off explicitly

### Commands

```
/secret              Toggle secret mode on/off
/secret on           Enable secret mode explicitly
/secret off          Disable secret mode explicitly
/secret <message>    One-shot: Ask this question secretly (doesn't toggle mode)
```

### Visual Indicator

When in secret mode, display above input prompt:
```
[🔒 SECRET MODE - Messages not saved to history]
```

### Implementation Notes

- Add `secret_mode: bool` to session state
- In REPL loop, check mode before adding messages to chat
- For `/secret <message>`, send immediately without storing, then continue normal mode
- Secret mode context = all messages before entering secret mode (frozen snapshot)

### Tasks

- [ ] Add `secret_mode` to `SessionState`
- [ ] Implement `/secret` command variants in `commands.py`
- [ ] Modify REPL loop to handle secret mode
- [ ] Add visual indicator in prompt area
- [ ] Ensure no messages are saved in secret mode

---

## 3. Delete Suffix Support (`--`)

### Description

Commands that set values should support `--` suffix (with space) to delete/clear the value.

### Affected Commands

| Command | Behavior |
|---------|----------|
| `/system --` | Remove system prompt from current chat session |
| `/title --` | Clear title from current chat |
| `/summary --` | Clear summary from current chat |

### Important Changes

- `/title` alone will **no longer clear title** - it will use AI to generate one
- `/summary` alone will **no longer clear summary** - it will use AI to generate one
- User must explicitly use `--` to delete

### Implementation

Modify command parsing to detect `--` as argument and call appropriate clear/delete logic.

### Tasks

- [ ] Update `/system` to support `--` for deletion
- [ ] Update `/title` to support `--` for deletion (change current behavior)
- [ ] Update `/summary` to support `--` for deletion (change current behavior)
- [ ] Update `/title` (no args) to call AI title generation
- [ ] Update `/summary` (no args) to call AI summary generation
- [ ] Update help text

---

## 4. Safe Command Implementation

### Description

The `/safe` command checks chat content for potentially unsafe or sensitive information before sharing.

### Behavior

```
/safe                Check entire chat for unsafe content
/safe <hex_id>       Check specific message
```

### Implementation

- Uses the **helper AI** (not chat AI) for analysis
- Scans for: PII, credentials, proprietary info, offensive content
- Returns categorized findings with severity levels

### Output Format

```
Safety Check Results:
━━━━━━━━━━━━━━━━━━━━━
✓ No PII detected
⚠ Potential API key found in message [a3f]
✓ No offensive content
━━━━━━━━━━━━━━━━━━━━━
```

### Tasks

- [ ] Implement `/safe` command
- [ ] Create safety check prompt for helper AI
- [ ] Parse and display results
- [ ] Add message-specific checking with hex IDs

---

## 5. Helper AI Model

### Terminology

| Term | Description |
|------|-------------|
| **Chat AI** | Primary AI for conversation (user ↔ assistant) |
| **Helper AI** | Secondary AI for background tasks (title/summary generation, safety checks, future smart context) |

### Rationale

The helper AI should be **independent** from the chat AI to ensure consistency:
- If user switches from Claude to DeepSeek mid-chat, summaries should remain consistent
- Helper AI generates titles, summaries, performs safety checks
- Avoids style inconsistencies across generated content

### Commands

```
/helper              Show current helper model
/helper <model>      Set helper model
/helper default      Revert to profile's default AI
```

### Profile Configuration

```json
{
  "default_ai": "claude",
  "default_helper_ai": "claude",  // Optional, defaults to default_ai if not set
  "models": {
    "openai": "gpt-5-mini",
    "claude": "claude-haiku-4-5",
    ...
  }
}
```

### Session State

Add to `SessionState`:
```python
helper_ai: str           # Current helper provider
helper_model: str        # Current helper model
```

### Implementation Notes

- If `default_helper_ai` not in profile, use `default_ai`
- Helper AI uses same API key configuration as regular providers
- Helper AI should use efficient/cheap models (e.g., `claude-haiku-4-5`, `gpt-5-mini`)

### Tasks

- [ ] Add `default_helper_ai` support to profile
- [ ] Add `helper_ai` and `helper_model` to session state
- [ ] Implement `/helper` command
- [ ] Create helper AI invocation function (non-streaming, simple request)
- [ ] Update title generation to use helper AI
- [ ] Update summary generation to use helper AI
- [ ] Update safety check to use helper AI

---

## 6. Revert to Default Values

### Description

All settings with profile defaults should be revertable using `default` argument.

### Commands

| Command | Effect |
|---------|--------|
| `/model default` | Revert to `profile.models[profile.default_ai]` |
| `/helper default` | Revert to `profile.default_helper_ai` or `profile.default_ai` |
| `/system default` | Revert to `profile.system_prompt` |
| `/timeout default` | Revert to `profile.timeout` (or 30 if not set) |

### Implementation

Each command handler checks for `"default"` argument and retrieves value from profile.

### Tasks

- [ ] Implement `/model default`
- [ ] Implement `/helper default`
- [ ] Implement `/system default`
- [ ] Implement `/timeout default`
- [ ] Update help text

---

## 7. Retry Command Fix

### Current Bug

Retry mode incorrectly adds temporary interactions to chat history.

### Correct Behavior

#### Scenario
1. Chat has 2 complete interactions (4 messages: U1→A1→U2→A2)
2. User doesn't like A2, initiates `/retry`
3. Retry mode begins

#### In Retry Mode
- App shows only U1→A1→U2 to AI (excludes A2)
- User can adjust prompt and get new responses
- Each attempt is **temporary** (not saved to history or RAM)
- User can try unlimited times

#### Exiting Retry Mode
- `/apply` - Replace last interaction with current retry attempt
  - Deletes U2 and A2 from history
  - Adds the retry's user message and AI response
  - Saves to file
- `/cancel` - Exit retry mode, keep original A2
  - Nothing changes in history
  - Return to normal mode

### Visual Indicator

When in retry mode, display above input prompt:
```
[🔄 RETRY MODE - Use /apply to accept, /cancel to abort]
```

### Implementation

Add to session state:
```python
retry_mode: bool = False
retry_base_messages: list = []  # Frozen snapshot of messages before retry
retry_current_attempt: tuple = None  # (user_msg, assistant_msg) of current attempt
```

### Tasks

- [ ] Fix retry mode to not modify history during retries
- [ ] Implement `/apply` command
- [ ] Implement `/cancel` command
- [ ] Store retry attempts temporarily
- [ ] Add visual indicator
- [ ] Update help text

---

## 8. Purge Command

### Description

Directly delete a single message by hex ID. Breaks conversation context intentionally.

### Command

```
/purge <hex_id>      Delete specific message
/purge <hex_id> <hex_id> ...   Delete multiple messages
```

### Behavior

- Deletes only the specified message(s)
- Does NOT delete following messages (unlike `/rewind`)
- Warns user about context breakage
- Requires confirmation for multiple messages

### Output

```
⚠ WARNING: Purging breaks conversation context
Purge message [a3f]? (y/n): y
Purged 1 message
```

### Tasks

- [ ] Implement `/purge` command
- [ ] Add confirmation prompt
- [ ] Support multiple hex IDs
- [ ] Save chat after purge

---

## 9. History/Show Commands

### Description

View chat history and individual messages.

### Commands

```
/history             Show recent messages (default: last 10)
/history <n>         Show last n messages
/history all         Show all messages
/history --errors    Show only error messages
/show <hex_id>       Show full content of specific message
```

### History Output Format

```
Chat History (showing 10 of 47 messages)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[a3f] 👤 User (2026-02-07 10:30)
  How do I implement authentication...

[b2c] 🤖 Assistant/claude-haiku-4-5 (2026-02-07 10:31)
  You can implement authentication using...

[c1d] ❌ Error (2026-02-07 10:35)
  API timeout after 30 seconds
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Show Output Format

```
Message [a3f] - User (2026-02-07 10:30:45)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
How do I implement authentication in a 
Flask application? I need to support:

1. Username/password login
2. OAuth with Google
3. Session management
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Tasks

- [ ] Implement `/history` command with options
- [ ] Implement `/show` command
- [ ] Add message truncation for history view
- [ ] Display hex IDs for all messages
- [ ] Format timestamps nicely

---

## 10. Smart Context Architecture

### Status: Future Feature (Architecture Preparation Only)

### Concept

Generate context-aware summaries for each message to enable super-long chats (1000+ interactions over years).

### Summary Generation Logic

For each message, send 3 messages to AI for context-aware summarization:
1. **User message 1**: "Summarize this so getting [Assistant message 1] is natural"
2. **Assistant message 1**: "Summarize this so [User 1] and [User 2] connect naturally via this summary"
3. Continue pattern: always include preceding and following message for context

### Storage Considerations

- Summaries are NOT source of truth (can be regenerated)
- May store in: chat history file, separate file, or SQLite database
- Could include vector embeddings for RAG

### Architecture Preparation

Add to message structure (optional fields):
```json
{
  "timestamp": "...",
  "role": "user",
  "content": [...],
  "summary": null,          // Future: context-aware summary
  "summary_model": null,    // Future: model used for summary
  "summary_at": null        // Future: when summary was generated
}
```

### Tasks

- [ ] Add optional summary fields to message schema
- [ ] Document summary generation algorithm
- [ ] No implementation yet - just architecture notes

---

## 11. Hex ID System

### Description

Each message gets a temporary hex ID for reference in commands.

### Characteristics

- 3+ digit hex ID (e.g., `a3f`, `b2c`, `1a4f`)
- Generated at runtime (not saved to history)
- Changes on each app run (acceptable)
- Unique within session

### Generation Algorithm

```python
def generate_hex_id(existing_ids: set[str], min_digits: int = 3) -> str:
    """Generate unique hex ID."""
    digits = min_digits
    max_attempts = 3
    
    while True:
        for _ in range(max_attempts):
            # Generate random hex
            hex_id = format(random.randint(0, 16**digits - 1), f'0{digits}x')
            if hex_id not in existing_ids:
                existing_ids.add(hex_id)
                return hex_id
        
        # All attempts failed, increase digits
        digits += 1
```

### Capacity

- 3 digits: 4,096 unique IDs
- 4 digits: 65,536 unique IDs
- With 3 attempts before increasing, most chats will use 3-digit IDs

### Implementation

Add to session state:
```python
message_hex_ids: dict[int, str] = {}  # message_index -> hex_id
hex_id_set: set[str] = set()          # for uniqueness checking
```

### Tasks

- [ ] Implement hex ID generation
- [ ] Assign IDs to messages on chat load
- [ ] Add ID lookup functions
- [ ] Update `/rewind` to accept hex IDs
- [ ] Use hex IDs in `/purge`, `/show`, `/history`

---

## 12. Miscellaneous

### 12.1 Error State Handling

When chat has a pending error (last message is error type):
- User cannot continue normal chat
- Must use `/retry` to retry or `/secret` to ask without saving
- Display indicator:
```
[⚠️ PENDING ERROR - Use /retry to retry or /secret to ask separately]
```

### 12.2 Current Directory Prohibition

**Critical:** Never use current directory for path resolution.

- All paths must use `~`, `@`, or be absolute
- Relative paths without prefix → raise `ValueError`
- Audit codebase for any `Path.cwd()` or relative path usage

### 12.3 Profile Read-Only Policy

Profiles are **read-only** at runtime:
- App never modifies profile files
- Session changes (model, timeout, etc.) are temporary
- Only chat history files are written

### 12.4 Update /rewind Command

- Accept hex IDs in addition to numeric indices
- `/rewind <hex_id>` - rewind to message with that ID
- `/rewind last` - still works

### 12.5 Help Text Updates

Update `/help` output to include all new commands:
- `/system`, `/secret`, `/helper`
- `/purge`, `/history`, `/show`
- `/apply`, `/cancel` (in retry mode)
- Document `--` suffix for deletion
- Document `default` for reversion

---

## Implementation Order

Recommended implementation sequence:

### Phase 1: Foundation
1. [ ] Hex ID System (#11) - needed by many other features
2. [ ] System Prompt Refactoring (#1) - terminology cleanup
3. [ ] Delete Suffix Support (#3) - command parsing

### Phase 2: Mode Support
4. [ ] Secret Mode (#2)
5. [ ] Retry Command Fix (#7)
6. [ ] Error State Handling (#12.1)

### Phase 3: Helper AI
7. [ ] Helper AI Model (#5)
8. [ ] Safe Command (#4)
9. [ ] AI Title/Summary Generation (part of #3)

### Phase 4: History Management
10. [ ] History/Show Commands (#9)
11. [ ] Purge Command (#8)
12. [ ] Revert to Defaults (#6)

### Phase 5: Polish
13. [ ] Update Help Text (#12.5)
14. [ ] Current Directory Audit (#12.2)
15. [ ] Smart Context Architecture Notes (#10)

---

## Testing Strategy

### Unit Tests

- Path mapping with new system prompt handling
- Hex ID generation uniqueness
- Command parsing for `--` suffix
- Mode state transitions

### Integration Tests

- Secret mode full flow
- Retry mode with apply/cancel
- Helper AI invocation
- History/show display

### Manual Testing

- Visual indicators display correctly
- Error state handling
- Multi-session hex ID uniqueness

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/poly_chat/cli.py` | Session state, REPL loop, mode indicators |
| `src/poly_chat/commands.py` | All new commands, command parsing |
| `src/poly_chat/chat.py` | Metadata field rename, message operations |
| `src/poly_chat/profile.py` | Helper AI config, path handling |
| `src/poly_chat/models.py` | (minor) Helper model support |
| `tests/*` | Update all affected tests |
| `README.md` | Document new features |

---

## Notes

- This plan represents a significant refactoring effort
- Implement incrementally with tests for each phase
- Maintain backward compatibility with existing chat history files
- Consider migration script for `system_prompt_key` → `system_prompt_path` rename

---

*Document created: 2026-02-07*
*Last updated: 2026-02-07*
