# Web Search Feature Implementation Plan for PolyChat

## Context

PolyChat supports 7 AI providers but none currently leverage their web search capabilities. Research shows that 5 of 7 providers have official search APIs. This plan adds a `/search` command (matching the existing `/secret` pattern) to enable web search across supported providers, with inline citation display.

**Providers with search:** OpenAI, Claude, Gemini, Grok, Perplexity (5)
**Providers without search:** Mistral (requires different SDK), DeepSeek (no API) (2)

---

## Step 1: Add Search Support Registry

**File:** `src/poly_chat/models.py`

Add a constant set of providers that support web search:

```python
SEARCH_SUPPORTED_PROVIDERS: set[str] = {
    "openai", "claude", "gemini", "grok", "perplexity",
}
```

Add a helper function:

```python
def provider_supports_search(provider: str) -> bool:
    return provider in SEARCH_SUPPORTED_PROVIDERS
```

---

## Step 2: Add `search_mode` to Session State

**File:** `src/poly_chat/app_state.py`

Add field to `SessionState` dataclass:

```python
search_mode: bool = False
```

**File:** `src/poly_chat/session_manager.py`

Add property (following `secret_mode` pattern at ~line 188):

```python
@property
def search_mode(self) -> bool:
    return self._state.search_mode

@search_mode.setter
def search_mode(self, value: bool) -> None:
    self._state.search_mode = bool(value)
```

Add to `_clear_chat_scoped_state()` (~line 332):

```python
self._state.search_mode = False
```

Add to `to_dict()` (~line 283):

```python
"search_mode": self._state.search_mode,
```

---

## Step 3: Add `/search` Command

**File:** `src/poly_chat/commands/runtime.py`

Add `search_mode_command()` method to `RuntimeCommandsMixin`, following the exact pattern of `secret_mode_command()` in `commands/misc.py`:

- `/search` (no args) → show status + which providers support it
- `/search on` → enable search mode (check provider supports it)
- `/search off` → disable search mode
- `/search <msg>` → one-shot search message (signal `__SEARCH_ONESHOT__:<msg>`)

When enabling, check `models.provider_supports_search(self.manager.current_ai)`. If not supported, return error message like: "Search not supported for {provider}. Supported: openai, claude, gemini, grok, perplexity"

**File:** `src/poly_chat/commands/__init__.py`

Register in `command_map` (~line 53):

```python
"search": self.search_mode_command,
```

**File:** `src/poly_chat/commands/misc.py`

Add to help text under "Chat Control:" section:

```
  /search           Show current search mode state
  /search on/off    Enable/disable web search
  /search <msg>     Send one search-enabled message
```

**File:** `src/poly_chat/commands/metadata.py`

Add to `show_status()` output under "Modes" section (~line 533):

```python
f"Search Mode:  {'ON' if self.manager.search_mode else 'OFF'}",
```

---

## Step 4: Update AI Provider Protocol

**File:** `src/poly_chat/ai/base.py`

Add `search: bool = False` parameter to both `send_message()` and `get_full_response()`:

```python
async def send_message(
    self,
    messages: list[dict],
    model: str,
    system_prompt: str | None = None,
    stream: bool = True,
    search: bool = False,       # NEW
) -> AsyncIterator[str]: ...

async def get_full_response(
    self,
    messages: list[dict],
    model: str,
    system_prompt: str | None = None,
    search: bool = False,       # NEW
) -> tuple[str, dict]: ...
```

---

## Step 5: Update AI Runtime

**File:** `src/poly_chat/ai_runtime.py`

Add `search: bool = False` parameter to `send_message_to_ai()`:

```python
async def send_message_to_ai(
    provider_instance: ProviderInstance,
    messages: list[dict],
    model: str,
    system_prompt: Optional[str] = None,
    provider_name: Optional[str] = None,
    mode: str = "normal",
    chat_path: Optional[str] = None,
    search: bool = False,           # NEW
) -> tuple:
```

Pass it to `provider_instance.send_message(... search=search ...)`.

Log `search=search` in the `log_event("ai_request", ...)` call.

---

## Step 6: Implement Provider Search — Perplexity (easiest)

**File:** `src/poly_chat/ai/perplexity_provider.py`

Perplexity Sonar models have search built-in. When `search=True`:

- In `_create_chat_completion()`, add an optional `search_options` parameter
- Pass through `web_search_options={}` (empty dict enables default search behavior, which is already the default for Sonar models)
- For `send_message()`: extract citations from streaming chunks (Perplexity returns them in the final chunk as `chunk.citations`)
- Store citations in `metadata["citations"]`

Minimal change since Perplexity already does search. The main addition is extracting/returning citations during streaming.

---

## Step 7: Implement Provider Search — OpenAI

**File:** `src/poly_chat/ai/openai_provider.py`

When `search=True`:

- In `_create_response()`, add `tools` parameter:
  ```python
  tools = [{"type": "web_search_preview"}] if search else None
  ```
- Pass `tools=tools` to `self.client.responses.create()`
- In streaming: handle new event types:
  - `response.web_search_call.searching` — log that search is happening
  - `response.web_search_call.completed` — search done
  - Continue yielding `response.output_text.delta` as before
- In `response.completed`: extract citations from `response.output` items' annotations (type `url_citation` with `url`, `title`)
- Store in `metadata["citations"]`

---

## Step 8: Implement Provider Search — Gemini

**File:** `src/poly_chat/ai/gemini_provider.py`

When `search=True`:

- In both `send_message()` and `get_full_response()`, add to the `GenerateContentConfig`:
  ```python
  tools = [types.Tool(google_search=types.GoogleSearch())] if search else None
  config = types.GenerateContentConfig(
      system_instruction=system_prompt if system_prompt else None,
      tools=tools,
  )
  ```
- Extract grounding metadata from response:
  - `response.candidates[0].grounding_metadata.grounding_chunks` → list of `{web: {uri, title}}`
- Store in `metadata["citations"]` as `[{"url": uri, "title": title}, ...]`

---

## Step 9: Implement Provider Search — Grok

**File:** `src/poly_chat/ai/grok_provider.py`

When `search=True`:

- In `_create_chat_completion()`, add `tools` parameter:
  ```python
  tools = [{"type": "web_search"}] if search else None
  ```
- Pass `tools=tools` to `self.client.chat.completions.create()`
- Extract citations from response: `getattr(response, "citations", None)` (similar to Perplexity)
- Store in `metadata["citations"]`

---

## Step 10: Implement Provider Search — Claude (most complex)

**File:** `src/poly_chat/ai/claude_provider.py`

When `search=True`:

- Add `tools` to kwargs in both methods:
  ```python
  if search:
      kwargs["tools"] = [{"type": "web_search_20250305", "name": "web_search"}]
  ```
- **Streaming complexity:** Claude's response now contains interleaved content blocks:
  1. `server_tool_use` (search query being executed)
  2. `web_search_tool_result` (search results)
  3. `text` blocks (with inline citations)
- In `send_message()`: Only yield text from `text` content blocks, skip tool-use blocks
- Handle `stop_reason == "pause_turn"` (search may cause the model to pause)
- Extract citations from text block `citations` annotations
- In `get_full_response()`: iterate `response.content` blocks, only extract `text` blocks, collect citations
- Store citations in `metadata["citations"]`
- Increase `max_tokens` when search is active (search responses tend to be longer) — e.g., `max_tokens=8192`

---

## Step 11: Add Citation Display

**File:** `src/poly_chat/streaming.py`

Add a function to display citations after the response:

```python
def display_citations(citations: list[dict]) -> None:
    """Display search citations after response."""
    if not citations:
        return
    print()
    print("Sources:")
    for i, citation in enumerate(citations, 1):
        title = citation.get("title", "")
        url = citation.get("url", "")
        if title and url:
            print(f"  [{i}] {title}")
            print(f"      {url}")
        elif url:
            print(f"  [{i}] {url}")
```

---

## Step 12: Update REPL

**File:** `src/poly_chat/repl.py`

### For persistent search mode (toggle):

In the `send_normal`/`send_retry`/`send_secret` handling block (~line 310-397):

- Determine search flag: `use_search = manager.search_mode`
- Pass `search=use_search` to `send_message_to_ai()`
- After `display_streaming_response()`, check `metadata.get("citations")` and call `display_citations()`

### For one-shot search:

In `handle_command_response` signal processing, detect `__SEARCH_ONESHOT__`:

**File:** `src/poly_chat/orchestrator.py`

Add handler for `__SEARCH_ONESHOT__:<msg>` in `handle_command_response()` (~line 139):

```python
if response.startswith("__SEARCH_ONESHOT__:"):
    return OrchestratorAction(
        action="search_oneshot",
        message=response.split(":", 1)[1]
    )
```

**File:** `src/poly_chat/repl.py`

Handle `search_oneshot` action:
- Same as `send_normal` flow (message IS saved to chat)
- But pass `search=True` to `send_message_to_ai()`
- Display citations after response

Add `search_oneshot` to the OrchestratorAction:

**File:** `src/poly_chat/orchestrator.py`

In `OrchestratorAction.action` docstring, add `"search_oneshot"` to valid action types.

Add `handle_search_oneshot_message()` method (follows `_handle_normal_message()` pattern):
- Adds user message to chat
- Returns `OrchestratorAction(action="search_oneshot", messages=messages, mode="normal", ...)`

---

## Step 13: Update Tests

**File:** `tests/test_session_state.py`
- Test `search_mode` defaults to `False`

**File:** `tests/test_session_manager.py`
- Test `search_mode` property get/set
- Test `search_mode` cleared on chat switch

**File:** `tests/test_commands_runtime.py`
- Test `/search` show status (on/off)
- Test `/search on` / `/search off` toggle
- Test `/search on` with unsupported provider (error message)
- Test `/search on` when already on
- Test `/search <msg>` returns `__SEARCH_ONESHOT__` signal

**File:** `tests/test_models.py`
- Test `provider_supports_search()` for all 7 providers

---

## Files Modified (Summary)

| File | Change |
|------|--------|
| `src/poly_chat/models.py` | Add `SEARCH_SUPPORTED_PROVIDERS`, `provider_supports_search()` |
| `src/poly_chat/app_state.py` | Add `search_mode` field |
| `src/poly_chat/session_manager.py` | Add `search_mode` property, clear on chat switch, add to `to_dict()` |
| `src/poly_chat/commands/runtime.py` | Add `search_mode_command()` |
| `src/poly_chat/commands/__init__.py` | Register `/search` in command_map |
| `src/poly_chat/commands/misc.py` | Update help text |
| `src/poly_chat/commands/metadata.py` | Update `/status` output |
| `src/poly_chat/ai/base.py` | Add `search` param to protocol |
| `src/poly_chat/ai_runtime.py` | Pass `search` flag through |
| `src/poly_chat/ai/perplexity_provider.py` | Extract citations from streaming |
| `src/poly_chat/ai/openai_provider.py` | Add `web_search_preview` tool, handle search events |
| `src/poly_chat/ai/gemini_provider.py` | Add Google Search grounding tool |
| `src/poly_chat/ai/grok_provider.py` | Add `web_search` tool |
| `src/poly_chat/ai/claude_provider.py` | Add web search tool, handle multi-block response |
| `src/poly_chat/streaming.py` | Add `display_citations()` |
| `src/poly_chat/repl.py` | Pass search flag, display citations, handle search_oneshot |
| `src/poly_chat/orchestrator.py` | Handle `__SEARCH_ONESHOT__` signal |
| `tests/test_session_state.py` | Test search_mode default |
| `tests/test_session_manager.py` | Test search_mode property |
| `tests/test_commands_runtime.py` | Test /search command |
| `tests/test_models.py` | Test provider_supports_search() |

## Implementation Order

1. Steps 1-3: Infrastructure (models, state, command) — can test `/search` command immediately
2. Step 4-5: Protocol + runtime plumbing
3. Step 6: Perplexity (simplest, validates the pipeline)
4. Step 7: OpenAI (clean Responses API)
5. Step 8: Gemini (clean google-genai)
6. Step 9: Grok (straightforward)
7. Step 10: Claude (most complex streaming)
8. Steps 11-12: Citation display + REPL integration
9. Step 13: Tests

## Verification

1. Run existing tests: `cd apps/poly-chat && python -m pytest tests/ -v`
2. Run new tests for search command, session state, and model support
3. Manual testing per provider (requires API keys):
   - `/search on` → send message → verify response includes citations
   - `/search What is the latest AI news?` → verify one-shot works and citations display
   - `/search off` → send message → verify no search
   - Switch to Mistral/DeepSeek → `/search on` → verify error message
   - `/status` → verify search mode shows in status output
