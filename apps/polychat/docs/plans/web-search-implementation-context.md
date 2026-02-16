# Web Search Implementation Context

> **Purpose:** Complete knowledge transfer for implementing web search in PolyChat.
> This document captures all codebase patterns, API specifics, and implementation details
> gathered during research (Feb 10, 2026). Read this before the plan file.

---

## 1. Codebase Architecture Overview

PolyChat is a Python CLI multi-AI chat tool at `apps/poly-chat/`. Key directories:

```
src/poly_chat/
  ai/                    # Provider implementations (7 files + base.py)
  commands/              # Command handlers (mixin architecture)
  keys/                  # API key loading
  ui/                    # Chat UI (file selection)
  app_state.py           # SessionState dataclass
  session_manager.py     # SessionManager wraps SessionState with properties
  ai_runtime.py          # Provider instantiation + send_message_to_ai()
  orchestrator.py        # Chat lifecycle, mode transitions, command signals
  repl.py                # Main REPL loop (drives everything)
  streaming.py           # Stream display + accumulation
  models.py              # Model registry, provider mapping
  chat.py                # Chat data load/save/manipulation
  message_formatter.py   # lines_to_text / text_to_lines conversion
  hex_id.py              # Message ID generation
  logging_utils.py       # Structured event logging
  profile.py             # Profile loading
  helper_ai.py           # Background AI tasks (title, summary)
  chat_manager.py        # File listing, creation, renaming
```

---

## 2. The 7 Providers — SDK and Base URLs

| Provider | File | SDK | Base URL | Search Support |
|----------|------|-----|----------|----------------|
| OpenAI | `openai_provider.py` | `openai` (AsyncOpenAI) Responses API | default (api.openai.com) | YES |
| Claude | `claude_provider.py` | `anthropic` (AsyncAnthropic) | default | YES |
| Gemini | `gemini_provider.py` | `google.genai` (genai.Client) | default | YES |
| Grok | `grok_provider.py` | `openai` (AsyncOpenAI) | `https://api.x.ai/v1` | YES |
| Perplexity | `perplexity_provider.py` | `openai` (AsyncOpenAI) | `https://api.perplexity.ai` | YES (always-on) |
| Mistral | `mistral_provider.py` | `openai` (AsyncOpenAI) | `https://api.mistral.ai/v1` | NO (needs Agents API) |
| DeepSeek | `deepseek_provider.py` | `openai` (AsyncOpenAI) | `https://api.deepseek.com` | NO (no API) |

---

## 3. Provider Implementation Pattern

Every provider has this structure (use as template):

```python
class XxxProvider:
    def __init__(self, api_key: str, timeout: float = 30.0):
        # Create async client with httpx.Timeout and max_retries=0

    def format_messages(self, chat_messages: list[dict]) -> list[dict]:
        # Convert PolyChat format [{"role": "user", "content": ["line1", "line2"]}]
        # to provider format [{"role": "user", "content": "line1\nline2"}]
        # Uses lines_to_text() from message_formatter

    @retry(...)  # tenacity decorator
    async def _create_xxx(self, ...):
        # Internal retried API call

    async def send_message(self, messages, model, system_prompt=None, stream=True, metadata=None):
        # Streaming: yields text chunks, populates metadata["usage"] after streaming

    async def get_full_response(self, messages, model, system_prompt=None):
        # Non-streaming: returns (text, metadata_dict)
```

**Important:** The `metadata` parameter in `send_message()` is a dict passed by reference. Providers populate `metadata["usage"]` with token counts after streaming completes. This is how usage data flows back to the caller.

---

## 4. Key Code Patterns to Follow

### 4.1 Command Registration

**File:** `commands/__init__.py` — `CommandHandler` class uses mixin inheritance:

```python
class CommandHandler(
    CommandHandlerBaseMixin,     # base.py: parse_command(), is_command(), switch_provider_shortcut()
    RuntimeCommandsMixin,        # runtime.py: set_model, set_helper, set_timeout, set_input_mode, etc.
    MetadataCommandsMixin,       # metadata.py: set_title, set_summary, show_status, etc.
    ChatFileCommandsMixin,       # chat_files.py: new_chat, open_chat, etc.
    MiscCommandsMixin,           # misc.py: show_help, exit_app, show_history, etc.
):
```

Command dispatch is a dictionary in `execute_command()`:

```python
command_map = {
    "model": self.set_model,
    "secret": self.secret_mode_command,
    # ... add "search": self.search_mode_command here
}
```

All command handlers: `async def handler(self, args: str) -> str`

### 4.2 Session State Pattern

**`app_state.py`** — `SessionState` is a `@dataclass` with fields. Add new fields with defaults.

**`session_manager.py`** — `SessionManager` wraps `SessionState` via `self._state`. Expose fields via `@property` / `@setter`. Key methods:

- `_clear_chat_scoped_state()` — clears retry_mode, secret_mode (add search_mode here)
- `to_dict()` — serializes state for diagnostics (add search_mode here)

### 4.3 The `/secret` Pattern (model for `/search`)

The `/secret` command in `commands/misc.py` (`secret_mode_command()`) is the exact template:

```python
async def secret_mode_command(self, args: str) -> str:
    # No args → show status
    # "on" → enable
    # "off" → disable
    # "on/off" → hint
    # anything else → one-shot signal: "__SECRET_ONESHOT__:<msg>"
```

The one-shot signal flows: command → orchestrator → REPL action.

### 4.4 Orchestrator Signal Flow

Commands return special `__SIGNAL__:data` strings. `orchestrator.handle_command_response()` detects them and returns `OrchestratorAction(action="xxx", ...)`. The REPL switches on `action.action`.

Current signals: `__EXIT__`, `__NEW_CHAT__:path`, `__OPEN_CHAT__:path`, `__CLOSE_CHAT__`, `__RENAME_CURRENT__:path`, `__DELETE_CURRENT__:name`, `__APPLY_RETRY__:hex_id`, `__CANCEL_RETRY__`, `__CLEAR_SECRET_CONTEXT__`, `__SECRET_ONESHOT__:msg`

### 4.5 REPL AI Call Chain

```
User input
  → orchestrator.handle_user_message()
  → OrchestratorAction(action="send_normal", messages=[...])
  → REPL:
      1. validate_and_get_provider(manager)
      2. send_message_to_ai(provider, messages, model, system_prompt, ...)
      3. display_streaming_response(stream)
      4. log_event("ai_response", ...)
      5. orchestrator.handle_ai_response(text, chat_path, chat_data, mode)
```

For search, the REPL needs to:
- Check `manager.search_mode` (toggle) or action type (one-shot)
- Pass `search=True` to `send_message_to_ai()`
- After streaming, check `metadata.get("citations")` and display them

---

## 5. Exact Search API Structures Per Provider

### 5.1 OpenAI (Responses API)

PolyChat uses `client.responses.create()`. Add `tools` parameter:

```python
# Current call:
await self.client.responses.create(model=model, input=input_items, stream=stream)

# With search:
await self.client.responses.create(
    model=model,
    input=input_items,
    stream=stream,
    tools=[{"type": "web_search_preview"}],  # Add this
)
```

**Streaming events to handle:**
- `response.web_search_call.searching` — search started (log only)
- `response.web_search_call.completed` — search done (log only)
- `response.output_text.delta` — text chunks (yield as before)
- `response.completed` — extract citations

**Citations in response:** In `event.response.output`, look for items with `type == "message"`. Their `content[].annotations[]` contain `url_citation` objects with `url`, `title`, `start_index`, `end_index`.

**Non-streaming:** `response.output_text` for text. Citations in `response.output[].content[].annotations[]`.

### 5.2 Claude (Anthropic SDK)

Add `tools` to the `kwargs` dict:

```python
if search:
    kwargs["tools"] = [{"type": "web_search_20250305", "name": "web_search"}]
```

**Streaming complexity:** This is the hardest provider. Claude's streaming with web search produces interleaved content blocks:

1. `content_block_start` with `server_tool_use` type (search query)
2. `content_block_start` with `web_search_tool_result` type (results — encrypted)
3. `content_block_start` with `text` type (model's response with citations)

The current streaming code uses `response_stream.text_stream` which auto-filters to text. This should still work for basic text extraction. However, citations need to be extracted from the `final_message.content` blocks:

```python
final_message = await response_stream.get_final_message()
for block in final_message.content:
    if hasattr(block, "text") and hasattr(block, "citations"):
        for citation in (block.citations or []):
            # citation has: cited_text, url, title, etc.
```

**Stop reason:** May be `"pause_turn"` instead of `"end_turn"` for search. Handle both.

**max_tokens:** Consider increasing from 4096 to 8192 when search is active.

### 5.3 Gemini (google-genai SDK)

Add `tools` to `GenerateContentConfig`:

```python
tools = [types.Tool(google_search=types.GoogleSearch())] if search else None
config = types.GenerateContentConfig(
    system_instruction=system_prompt if system_prompt else None,
    tools=tools,
)
```

**Citations:** Available in `response.candidates[0].grounding_metadata`:
- `.web_search_queries` — list of search queries executed
- `.grounding_chunks` — list with `.web.uri` and `.web.title`
- `.grounding_supports` — maps text segments to source chunks

For streaming, grounding metadata is in the final chunk's candidates.

### 5.4 Grok (xAI, OpenAI-compatible)

Add `tools` to `chat.completions.create()`:

```python
# Current call (in _create_chat_completion):
await self.client.chat.completions.create(
    model=model, messages=messages, stream=stream, stream_options=stream_options
)

# With search - add tools:
tools = [{"type": "web_search"}] if search else None
await self.client.chat.completions.create(
    model=model, messages=messages, stream=stream,
    stream_options=stream_options, tools=tools,
)
```

**Citations:** `getattr(response, "citations", None)` — returns list of URLs/titles.

**Note:** The `tools` parameter here is NOT a function-calling tool. It's a built-in server-side tool type specific to xAI's API. The OpenAI SDK may not validate the `type: "web_search"` value, but the xAI backend handles it.

### 5.5 Perplexity (OpenAI-compatible)

Search is always-on for Sonar models. No explicit enable needed. Optionally add filtering:

```python
# In _create_chat_completion, optionally add:
extra_body = None
if search:
    extra_body = {
        "web_search_options": {}  # empty = defaults; can add domain/recency filters
    }

await self.client.chat.completions.create(
    model=model, messages=messages, stream=stream,
    stream_options=stream_options,
    extra_body=extra_body,
)
```

**Citations:** Already partially implemented (line 249 of perplexity_provider.py). In `get_full_response()`:
```python
citations = getattr(response, "citations", None)
```
Returns a list of URL strings. For streaming, citations appear in the final chunk.

**Key insight:** Perplexity already returns search results by default. The `search` flag mainly controls whether we extract and display citations. The existing code already extracts them in `get_full_response()` but not in `send_message()`.

---

## 6. Document Accuracy Notes

The four research documents have some inaccuracies:

1. **`poly-chat-providers-copilot-analysis.md`** — WRONG about Claude ("LIMITED/no web search") and Mistral ("NO NATIVE SUPPORT"). Claude has full web search since May 2025. Mistral has search via Agents API. This doc's summary table is outdated.

2. **`claude-ai-provider-search-features-2026.md`** — References future-dated OpenAI models (`gpt-5-search-api-2026-10-14`). These don't exist yet (it's Feb 2026). OpenAI search works via `web_search_preview` tool in Responses API with existing models.

3. **`poly-chat-provider-search-codex-2026-02-09.md`** — Concise and accurate.

4. **`ai-providers-search-gemini.md`** — Accurate.

**Corrected status:** 6/7 providers have search APIs. We implement 5 (skip Mistral due to different SDK requirement, skip DeepSeek due to no API).

---

## 7. Key Files and Line References

### Core files to modify:

| File | Key Lines | What to Change |
|------|-----------|----------------|
| `models.py` | After line 82 | Add `SEARCH_SUPPORTED_PROVIDERS` set + helper |
| `app_state.py:SessionState` | Line 29 (after `secret_mode`) | Add `search_mode: bool = False` |
| `session_manager.py` | ~Line 188 (after secret_mode property) | Add `search_mode` property |
| `session_manager.py` | ~Line 332 (`_clear_chat_scoped_state`) | Add `self._state.search_mode = False` |
| `session_manager.py` | ~Line 283 (`to_dict`) | Add `"search_mode"` key |
| `commands/runtime.py` | End of class | Add `search_mode_command()` method |
| `commands/__init__.py` | ~Line 53 (command_map) | Add `"search": self.search_mode_command` |
| `commands/misc.py` | ~Line 65 (help text) | Add search command entries |
| `commands/metadata.py` | ~Line 533 (show_status Modes section) | Add Search Mode line |
| `ai/base.py` | Lines 15, 38 | Add `search: bool = False` to both methods |
| `ai_runtime.py` | Line 67 (`send_message_to_ai`) | Add `search` param, pass to provider |
| `ai/openai_provider.py` | Lines 84, 95 | Add `tools` param to `_create_response()` |
| `ai/claude_provider.py` | Lines 138, 229 | Add `tools` to kwargs when search=True |
| `ai/gemini_provider.py` | Lines 99, 186 | Add tools to GenerateContentConfig |
| `ai/grok_provider.py` | Lines 84, 96 | Add `tools` param to `_create_chat_completion()` |
| `ai/perplexity_provider.py` | Lines 114, 127 | Add `extra_body` for web_search_options |
| `streaming.py` | After line 82 | Add `display_citations()` function |
| `orchestrator.py` | ~Line 139 | Add `__SEARCH_ONESHOT__` handler |
| `repl.py` | ~Line 310 | Pass search flag, display citations |

### Test files to update:

| File | What to Add |
|------|-------------|
| `tests/test_session_state.py` | Test `search_mode` default |
| `tests/test_session_manager.py` | Test property, chat switch clears it |
| `tests/test_commands_runtime.py` | Test all `/search` command variants |
| `tests/test_models.py` | Test `provider_supports_search()` |

---

## 8. Dependencies and Config

**No new Python packages needed.** All search features use existing SDKs:
- `openai` — already installed (for OpenAI, Grok, Perplexity, Mistral, DeepSeek)
- `anthropic` — already installed (for Claude)
- `google-genai` — already installed (for Gemini)

**pyproject.toml:** No changes needed.

---

## 9. Testing

Run existing tests first to establish baseline:
```bash
cd apps/poly-chat && python -m pytest tests/ -v
```

Tests use `conftest.py` fixtures:
- `mock_session_manager` — creates a SessionManager with test profile
- `command_handler` — creates CommandHandler from mock_session_manager
- `sample_chat` — test chat data
- `temp_dir` — temporary directory

Test pattern for commands (see `test_commands_runtime.py`):
```python
@pytest.mark.asyncio
async def test_search_no_args_shows_state_off(command_handler, mock_session_manager):
    result = await command_handler.search_mode_command("")
    assert result == "Search mode: off"
    assert mock_session_manager.search_mode is False
```

---

## 10. Gotchas and Edge Cases

1. **Mistral `stream_options`:** Mistral rejects `stream_options` with 422. If adding extra params for search, be careful not to break Mistral's existing flow. (Mistral gets no search anyway.)

2. **Perplexity role alternation:** `format_messages()` merges consecutive same-role messages. This still applies with search.

3. **DeepSeek aggressive retries:** 10 attempts vs 4 for others. Search doesn't apply but don't accidentally break this.

4. **Claude `text_stream` auto-filtering:** The `response_stream.text_stream` helper already filters to text-only content, which is convenient for search (automatically skips tool_use blocks). But for citation extraction, you need `get_final_message()`.

5. **OpenAI Responses API event types:** The streaming loop currently handles `response.output_text.delta`, `response.completed`, and `response.output_item.done`. New search events (`response.web_search_call.*`) should be logged but not yield text.

6. **Provider cache invalidation:** Providers are cached by `(provider_name, api_key)` in SessionManager. Search toggle doesn't need new provider instances since search is a per-request parameter (passed in the API call), not a client-level config.

7. **Timeout:** Search queries take 5-30 seconds. Consider logging a note when search is active with low timeout. The existing timeout config applies to the `read` timeout which covers time-to-first-token.

8. **Citation deduplication:** Multiple providers may return duplicate URLs in citations. Consider deduplicating by URL before display.
