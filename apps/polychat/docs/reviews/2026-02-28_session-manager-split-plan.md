# SessionManager Responsibility Split

## Problem

`SessionManager` (460 lines, 34 methods) is a god class with five distinct
responsibilities, each with independent reasons to change:

| Responsibility | Methods | Consumers |
|---|---|---|
| **Retry mode state machine** | `enter_retry_mode`, `exit_retry_mode`, `get_retry_context`, `add_retry_attempt`, `get_retry_attempt`, `get_latest_retry_attempt_id`, `get_retry_target_index`, `reserve_hex_id`, `release_hex_id` (9 methods) | `orchestration/message_entry.py`, `orchestration/response_handlers.py`, `orchestration/signals.py`, `commands/runtime_modes.py`, `commands/meta_inspection.py`, `repl/loop.py` |
| **Secret mode state machine** | `enter_secret_mode`, `exit_secret_mode`, `get_secret_context` (3 methods) | `orchestration/message_entry.py`, `orchestration/signals.py`, `commands/runtime_modes.py`, `commands/meta_inspection.py`, `repl/loop.py` |
| **Hex ID management** | `assign_message_hex_id`, `get_message_hex_id`, `remove_message_hex_id`, `pop_message`, `message_hex_ids` (5 methods) | `orchestration/message_entry.py`, `orchestration/response_handlers.py`, `commands/runtime_mutation.py` |
| **Provider caching** | `get_cached_provider`, `cache_provider`, `clear_provider_cache`, `switch_provider` (4 methods) | `ai/runtime.py` (via `SessionContext` protocol), `commands/base.py` |
| **Chat lifecycle + session plumbing** | `switch_chat`, `close_chat`, `save_current_chat`, `clear_chat_scoped_state`, `to_dict`, `set_timeout`, `reset_timeout_to_default`, `format_timeout`, `default_timeout`, `load_system_prompt`, `toggle_input_mode` + `StateField` descriptors + `__init__` (13 methods) | everywhere |

Evidence this causes real problems:
- We just fixed a crash caused by stale state duplication — the god class made it
  tempting to pass copies instead of reading from the single owner.
- `SessionState` dataclass mixes retry fields, secret fields, provider cache, hex IDs,
  and session metadata in one flat bag of 20+ fields.
- Tests for retry mode need a full `SessionManager` with profile, chat, etc. —
  unrelated setup for the behavior under test.

## Approach

Extract retry and secret mode into standalone controller classes. These are the two
state machines with the clearest boundaries: they have enter/exit transitions, guarded
accessors, and mutual exclusion (`cannot enter retry while in secret` and vice versa).

Hex ID management and provider caching stay in `SessionManager` for now — they're
small, stable, and their consumers already access them through the manager. Extracting
them would add complexity without solving a real problem.

### What changes

1. **New file: `session/retry_controller.py`** — `RetryController` class owning all
   retry state and operations. Encapsulates: `retry_mode`, `retry_base_messages`,
   `retry_target_index`, `retry_attempts`, and the `hex_id_set` interaction for
   retry attempt IDs.

2. **New file: `session/secret_controller.py`** — `SecretController` class owning
   secret mode state. Encapsulates: `secret_mode`, `secret_base_messages`.

3. **`SessionState`** — retry and secret fields move into the controllers. The
   dataclass shrinks from ~20 fields to ~14. Controllers are composed as fields.

4. **`SessionManager`** — delegates retry/secret operations to controllers. The 12
   retry+secret methods become thin forwarding or are removed entirely (callers
   access `manager.retry` / `manager.secret` directly).

5. **`session/operations.py`** — retry/secret functions move into the controller
   classes. The operations module shrinks significantly.

6. **Consumers** — callers that use `manager.retry_mode` / `manager.enter_retry_mode()`
   switch to `manager.retry.active` / `manager.retry.enter()` (or similar).

### What does NOT change

- `StateField` descriptors — they remain for the session-level fields.
- Provider caching — stays in `SessionState` / `SessionManager`.
- Hex ID management — stays. The retry controller receives a reference to `hex_id_set`
  for managing retry attempt IDs, but the set itself stays in session state.
- Chat lifecycle (`switch_chat`, `close_chat`, `save_current_chat`) — stays.
- `ai/runtime.py` `SessionContext` protocol — not affected.
- All external behavior — this is a pure internal restructuring.

## Detailed Design

### RetryController

```python
@dataclass
class RetryController:
    """Retry mode state machine."""

    _hex_id_set: set[str]  # shared reference from SessionState

    active: bool = False
    base_messages: list[ChatMessage] = field(default_factory=list)
    target_index: int | None = None
    attempts: dict[str, RetryAttempt] = field(default_factory=dict)

    def enter(self, base_messages: list[ChatMessage], target_index: int | None = None) -> None: ...
    def exit(self) -> None: ...
    def get_context(self) -> list[ChatMessage]: ...
    def add_attempt(self, user_msg, assistant_msg, ...) -> str: ...
    def get_attempt(self, hex_id: str) -> RetryAttempt | None: ...
    def latest_attempt_id(self) -> str | None: ...
    def reserve_hex_id(self) -> str: ...
    def release_hex_id(self, hex_id: str) -> None: ...
    def clear(self) -> None: ...
```

### SecretController

```python
@dataclass
class SecretController:
    """Secret mode state machine."""

    active: bool = False
    base_messages: list[ChatMessage] = field(default_factory=list)

    def enter(self, base_messages: list[ChatMessage]) -> None: ...
    def exit(self) -> None: ...
    def get_context(self) -> list[ChatMessage]: ...
    def clear(self) -> None: ...
```

### Mutual exclusion

Currently enforced in `operations.py`:
- `enter_retry_mode` raises if `state.secret_mode`
- `enter_secret_mode` raises if `state.retry_mode`

After extraction, each controller needs a reference to the other's `active` flag.
Cleanest approach: each `enter()` receives a `check` callable:
```python
def enter(self, base_messages, ...) -> None:
    if self._conflict_check():
        raise ValueError("Cannot enter retry mode while in secret mode")
    ...
```
The manager wires: `retry._conflict_check = lambda: self.secret.active`

### SessionManager after

```python
class SessionManager:
    # StateField descriptors for session-level fields (unchanged)
    current_ai = StateField[str]("current_ai")
    ...

    retry: RetryController   # exposed directly
    secret: SecretController  # exposed directly

    def __init__(self, ...):
        ...
        self.retry = RetryController(hex_id_set=self._state.hex_id_set)
        self.secret = SecretController()
        self.retry._conflict_check = lambda: self.secret.active
        self.secret._conflict_check = lambda: self.retry.active

    # Retry/secret methods REMOVED — callers use manager.retry.* / manager.secret.*
```

### Consumer migration examples

```python
# Before:
manager.enter_retry_mode(base_messages, target_index=idx)
if manager.retry_mode: ...
context = manager.get_retry_context()
manager.exit_retry_mode()

# After:
manager.retry.enter(base_messages, target_index=idx)
if manager.retry.active: ...
context = manager.retry.get_context()
manager.retry.exit()
```

## Execution Order

1. Create `RetryController` in `session/retry_controller.py` — self-contained, testable
2. Create `SecretController` in `session/secret_controller.py` — same
3. Wire controllers into `SessionState` / `SessionManager` — compose, don't inherit
4. Migrate consumers — update all call sites (6 retry consumers, 5 secret consumers)
5. Move operations — move retry/secret functions from `operations.py` into controllers
6. Update `clear_chat_scoped_state` — call `retry.clear()` + `secret.clear()`
7. Clean up `SessionState` — remove retry/secret fields that moved into controllers
8. Run tests, fix failures
9. Verify no remaining references to old method names

## Risk

- **Medium**: many call sites to update (~30 references across 6 files for retry,
  ~15 across 5 files for secret). Mitigated by doing it in one pass with find/replace.
- **Low**: tests already cover retry and secret mode thoroughly. Regressions will surface.
- **Low**: no external API changes — this is internal refactoring only.
