# PolyChat Architecture

This document describes the architecture of PolyChat after the comprehensive refactoring completed in Tasks #1-11.

## Table of Contents

1. [Overview](#overview)
2. [Core Components](#core-components)
3. [SessionManager](#sessionmanager)
4. [ChatOrchestrator](#chatorchestrator)
5. [Command System](#command-system)
6. [REPL Flow](#repl-flow)
7. [State Management](#state-management)
8. [Provider Caching](#provider-caching)
9. [Testing Architecture](#testing-architecture)
10. [Data Flow](#data-flow)

## Overview

PolyChat is a multi-AI CLI chat tool that allows users to interact with multiple AI providers (OpenAI, Claude, Gemini, etc.) through a unified interface. The architecture has been refactored to achieve:

- **Single Source of Truth**: SessionManager eliminates session/session_dict duality
- **Separation of Concerns**: ChatOrchestrator extracts orchestration logic from REPL
- **Testability**: Clean interfaces enable comprehensive unit testing
- **Maintainability**: Clear component boundaries and responsibilities

## Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                         REPL Loop                            │
│  - User input (prompt_toolkit)                              │
│  - Display streaming responses                              │
│  - Error handling                                           │
└──────────┬──────────────────────────────────────────────────┘
           │
           ├──────────────────────────────────────────────────┐
           │                                                   │
           ▼                                                   ▼
┌──────────────────────┐                          ┌──────────────────────┐
│  SessionManager      │                          │  ChatOrchestrator    │
│  - Session state     │◄─────────────────────────│  - Command signals   │
│  - Chat data         │                          │  - Mode transitions  │
│  - Provider info     │                          │  - Message handling  │
│  - Hex ID management │                          │  - Error recovery    │
└──────────┬───────────┘                          └──────────┬───────────┘
           │                                                  │
           │                                                  │
           ▼                                                  ▼
┌──────────────────────┐                          ┌──────────────────────┐
│  CommandHandler      │                          │  AI Runtime          │
│  - Command parsing   │                          │  - Provider instances│
│  - Command execution │                          │  - Message sending   │
│  - State updates     │                          │  - Streaming         │
└──────────────────────┘                          └──────────────────────┘
```

## SessionManager

**Location**: `src/poly_chat/session_manager.py`

SessionManager is the **single source of truth** for all session state. It wraps `SessionState` (from `app_state.py`) and provides a clean interface for state access and modification.

### Responsibilities

1. **State Access**: Provides property-based access to session state
2. **State Transitions**: Encapsulates complex state changes (chat switching, mode changes)
3. **Hex ID Management**: Automatic hex ID assignment and tracking
4. **Provider Caching**: Manages cached AI provider instances
5. **Backward Compatibility**: Supports dict-like access for gradual migration

### Key Methods

```python
class SessionManager:
    # State access
    @property
    def current_ai(self) -> str
    @property
    def current_model(self) -> str
    @property
    def chat(self) -> Optional[dict]

    # State transitions
    def switch_provider(self, ai: str, model: str)
    def switch_chat(self, chat_path: str, chat_data: dict)
    def enter_retry_mode(self, base_messages: list)
    def exit_retry_mode(self)
    def enter_secret_mode(self)
    def exit_secret_mode(self)

    # Hex ID management
    def assign_message_hex_id(self, message_index: int) -> str

    # Utilities
    def to_dict(self) -> dict  # For backward compatibility
```

### Example Usage

```python
# Initialize
manager = SessionManager(
    profile=profile_data,
    current_ai="claude",
    current_model="claude-haiku-4-5",
    chat=chat_data,
)

# Property access (preferred)
print(manager.current_ai)  # "claude"
manager.switch_provider("openai", "gpt-5-mini")

# State transitions
manager.enter_retry_mode(base_messages)
manager.switch_chat(new_chat_path, new_chat_data)
```

## ChatOrchestrator

**Location**: `src/poly_chat/orchestrator.py`

ChatOrchestrator extracts all orchestration logic from the REPL loop, making the REPL thin and focused solely on UI concerns.

### Responsibilities

1. **Command Signal Processing**: Handles special command signals (`__NEW_CHAT__`, `__OPEN_CHAT__`, etc.)
2. **Mode Transitions**: Manages retry mode, secret mode, and normal mode
3. **Message Handling**: Processes user messages in different modes
4. **Error Recovery**: Handles AI errors and user cancellations
5. **Action Communication**: Returns structured actions for REPL to execute

### Command Signals

The orchestrator processes these command signals:

| Signal | Description |
|--------|-------------|
| `__EXIT__` | Exit the application |
| `__NEW_CHAT__:<path>` | Switch to new chat |
| `__OPEN_CHAT__:<path>` | Open existing chat |
| `__CLOSE_CHAT__` | Close current chat |
| `__APPLY_RETRY__` | Apply retry changes |
| `__CANCEL_RETRY__` | Cancel retry mode |
| `__SECRET_ONESHOT__:<msg>` | Send secret one-shot message |
| `__ENTER_RETRY__` | Enter retry mode |
| `__ENTER_SECRET__` | Enter secret mode |
| `__EXIT_SECRET__` | Exit secret mode |

### OrchestratorAction

The orchestrator returns `OrchestratorAction` dataclass to communicate with REPL:

```python
@dataclass
class OrchestratorAction:
    action: str  # Action type
    message: Optional[str] = None  # Display message
    chat_path: Optional[str] = None  # New chat path
    chat_data: Optional[dict] = None  # New chat data
    messages: Optional[list] = None  # Messages to send to AI
    mode: Optional[str] = None  # AI mode (normal/retry/secret)
```

### Action Types

| Action Type | Description |
|-------------|-------------|
| `continue` | Continue REPL loop (possibly with state changes) |
| `break` | Exit REPL loop |
| `print` | Display message to user |
| `send_normal` | Send message to AI in normal mode |
| `send_retry` | Send message to AI in retry mode |
| `send_secret` | Send message to AI in secret mode |
| `secret_oneshot` | Send one-shot secret message |

### Example Usage

```python
orchestrator = ChatOrchestrator(manager, session_dict)

# Handle command response
action = await orchestrator.handle_command_response(
    response="__NEW_CHAT__:/path/to/chat.json",
    current_chat_path="/old/chat.json",
    current_chat_data=old_chat
)

if action.action == "continue":
    chat_path = action.chat_path
    chat_data = action.chat_data
    print(action.message)

# Handle user message
action = await orchestrator.handle_user_message(
    user_input="Hello, AI!",
    chat_path=chat_path,
    chat_data=chat_data
)

if action.action == "send_normal":
    # Send to AI with action.messages
    pass
```

## Command System

**Location**: `src/poly_chat/commands/`

The command system is organized into mixins for different command categories:

```
CommandHandler (façade)
├── CommandHandlerBaseMixin (base.py)
│   └── Shared helpers (require_open_chat, save_current_chat, etc.)
├── RuntimeCommandsMixin (runtime.py)
│   └── /model, /timeout, /input
├── MetadataCommandsMixin (metadata.py)
│   └── /title, /summary, /prompt
├── ChatFileCommandsMixin (chat_files.py)
│   └── /new, /open, /close, /list, /save
└── MiscCommandsMixin (misc.py)
    └── /retry, /apply, /cancel, /secret, /help, /history, /show, /purge, /safe
```

### CommandHandler Signature

After refactoring, CommandHandler accepts:

```python
def __init__(self, manager: SessionManager, session_dict: dict):
    """
    Args:
        manager: SessionManager for unified state access
        session_dict: Dict containing REPL-specific paths
                     (profile_path, chat_path, log_file)
    """
```

### Command Flow

```
User Input → CommandHandler.execute_command()
           → Parse command and args
           → Route to appropriate mixin method
           → Method accesses/modifies state via self.manager
           → Return response string or special signal
           → ChatOrchestrator processes signal
           → REPL executes action
```

## REPL Flow

**Location**: `src/poly_chat/repl.py`

The REPL has been simplified to focus on UI concerns:

```
┌────────────────────────────────────────────────────────────┐
│ 1. Initialize SessionManager and ChatOrchestrator          │
└────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────────────┐
│ 2. Setup prompt_toolkit with keybindings                   │
└────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────────────┐
│ 3. Main Loop                                               │
│   ┌──────────────────────────────────────────────────────┐ │
│   │ a. Get user input                                    │ │
│   │ b. Is command?                                       │ │
│   │    YES → Execute command → Orchestrator handles      │ │
│   │    NO  → Orchestrator handles user message           │ │
│   │ c. Process OrchestratorAction                        │ │
│   │    - Update local state (chat_path, chat_data)       │ │
│   │    - Display messages                                │ │
│   │    - Send to AI if needed                            │ │
│   │ d. Handle streaming response                         │ │
│   │ e. Update state with AI response                     │ │
│   └──────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────┘
```

### Key Simplifications

Before refactoring, `repl.py` was 571 lines with a 200+ line if/elif chain. After refactoring:

- **332 lines** (42% reduction)
- Orchestration logic extracted to ChatOrchestrator
- Command signals processed by orchestrator
- REPL focuses on: input, display, and delegating to orchestrator

## State Management

### SessionState (app_state.py)

The underlying state container:

```python
@dataclass
class SessionState:
    # Core state
    current_ai: str
    current_model: str
    helper_ai: str
    helper_model: str
    profile: dict
    chat: Optional[dict]

    # System prompts
    system_prompt: Optional[str]
    system_prompt_path: Optional[str]

    # Mode flags
    retry_mode: bool = False
    retry_base_messages: Optional[list] = None
    secret_mode: bool = False
    input_mode: str = "quick"

    # Hex ID tracking
    message_hex_ids: dict[int, str] = field(default_factory=dict)
    hex_id_set: set[str] = field(default_factory=set)

    # Provider caching
    _provider_cache: dict[tuple[str, str], Any] = field(default_factory=dict)
```

### State Transitions

State transitions are encapsulated in SessionManager methods:

#### Chat Switching

```python
def switch_chat(self, chat_path: str, chat_data: dict):
    """Switch to a different chat, clearing chat-scoped state."""
    self._state.chat = chat_data
    initialize_message_hex_ids(self._state)
    self._clear_chat_scoped_state()
```

#### Retry Mode

```python
def enter_retry_mode(self, base_messages: list):
    """Enter retry mode with base messages."""
    if self._state.secret_mode:
        raise ValueError("Cannot enter retry mode while in secret mode")
    self._state.retry_mode = True
    self._state.retry_base_messages = base_messages.copy()

def exit_retry_mode(self):
    """Exit retry mode, clearing retry state."""
    self._state.retry_mode = False
    self._state.retry_base_messages = None
```

#### Secret Mode

```python
def enter_secret_mode(self):
    """Enter secret mode (messages not saved to history)."""
    if self._state.retry_mode:
        raise ValueError("Cannot enter secret mode while in retry mode")
    self._state.secret_mode = True

def exit_secret_mode(self):
    """Exit secret mode."""
    self._state.secret_mode = False
```

### Chat-Scoped State

When switching chats, these fields are reset:

- `retry_mode`
- `retry_base_messages`
- `secret_mode`
- `message_hex_ids`
- `hex_id_set`

This ensures mode flags don't leak between chats.

## Provider Caching

AI provider instances are cached to avoid recreating them on every request.

### Cache Key

Cache key is `(provider_name, api_key)`:

```python
def get_cached_provider(self, provider_name: str, api_key: str):
    """Get cached provider instance if available."""
    return self._provider_cache.get((provider_name, api_key))

def cache_provider(self, provider_name: str, api_key: str, instance):
    """Cache a provider instance."""
    self._provider_cache[(provider_name, api_key)] = instance
```

### Cache Lifecycle

- Created on first use
- Persists across messages in same session
- Cleared when switching providers (via `switch_provider`)
- **TODO**: Clear cache when timeout changes (not yet implemented)

## Testing Architecture

### Test Fixtures (conftest.py)

The refactoring introduced SessionManager-based fixtures:

```python
@pytest.fixture
def mock_session_manager():
    """Central fixture for SessionManager with basic state."""
    return SessionManager(
        profile={"default_ai": "claude", ...},
        current_ai="claude",
        current_model="claude-haiku-4-5",
        chat={"metadata": {}, "messages": []},
    )

@pytest.fixture
def mock_session_dict():
    """Central fixture for session_dict with REPL paths."""
    return {
        "profile_path": "/test/profile.json",
        "chat_path": "/test/chat.json",
        "log_file": "/test/log.txt",
    }

@pytest.fixture
def command_handler(mock_session_manager, mock_session_dict):
    """Central fixture for CommandHandler."""
    return CommandHandler(mock_session_manager, mock_session_dict)
```

### Custom Fixtures

Tests with specific requirements (like messages in chat) create custom fixtures:

```python
@pytest.fixture
def mock_session_manager_with_messages():
    """Custom fixture with pre-populated messages."""
    chat_data = {
        "metadata": {},
        "messages": [
            {"role": "user", "content": ["Hello"]},
            {"role": "assistant", "content": ["Hi there!"]},
        ]
    }

    manager = SessionManager(
        profile={...},
        current_ai="claude",
        current_model="claude-haiku-4-5",
        chat=chat_data,
    )

    # Set up hex IDs as expected by tests
    manager._state.message_hex_ids = {0: "a3f", 1: "b2c"}
    manager._state.hex_id_set = {"a3f", "b2c"}

    return manager
```

### Test Organization

- **test_session_state.py**: SessionState tests (102 tests)
- **test_orchestrator.py**: ChatOrchestrator tests (22 tests)
- **test_commands_*.py**: Command handler tests (grouped by category)
- **test_streaming.py**: Streaming response tests (14 tests)

**Total**: 330 tests, all passing

## Data Flow

### Normal Message Flow

```
User Input: "Hello, AI!"
     │
     ▼
ChatOrchestrator.handle_user_message()
     │
     ├─ Check mode (normal/retry/secret)
     ├─ Get messages from chat
     ├─ Append user message (if not secret)
     │
     ▼
Return OrchestratorAction(action="send_normal", messages=..., mode="normal")
     │
     ▼
REPL: Send to AI via ai_runtime.send_message_to_ai()
     │
     ├─ Get provider instance (cached or create)
     ├─ Send messages to provider
     ├─ Return response stream
     │
     ▼
REPL: display_streaming_response(stream)
     │
     ├─ Display chunks in real-time
     ├─ Accumulate full response
     │
     ▼
Return accumulated response text
     │
     ▼
ChatOrchestrator.handle_ai_response()
     │
     ├─ Append assistant response to chat
     ├─ Save chat to file
     ├─ Clear retry mode if active
     │
     ▼
REPL: Display token usage, continue loop
```

### Command Flow with Signals

```
User Input: "/new my-chat"
     │
     ▼
CommandHandler.execute_command()
     │
     ├─ Parse: command="new", args="my-chat"
     ├─ Route to create_new_chat()
     │
     ▼
create_new_chat(args)
     │
     ├─ Create new chat file
     ├─ Get chat path
     │
     ▼
Return "__NEW_CHAT__:/path/to/my-chat.json"
     │
     ▼
ChatOrchestrator.handle_command_response()
     │
     ├─ Parse signal: type="__NEW_CHAT__", path="..."
     ├─ Load new chat data
     ├─ manager.switch_chat(path, data)
     │
     ▼
Return OrchestratorAction(
    action="continue",
    chat_path="/path/to/my-chat.json",
    chat_data=new_chat,
    message="Opened chat: my-chat.json"
)
     │
     ▼
REPL: Update local state, display message, continue
```

### Retry Flow

```
User: "Fix the code"
     │
     ▼
ChatOrchestrator.handle_user_message()
     │
     ├─ Mode: retry
     ├─ Get retry_base_messages
     ├─ Append user message
     │
     ▼
Return OrchestratorAction(action="send_retry", messages=retry_messages, mode="retry")
     │
     ▼
REPL: Send to AI with retry messages
     │
     ▼
AI Response (streaming)
     │
     ▼
ChatOrchestrator.handle_ai_response(mode="retry")
     │
     ├─ Replace error message with new response
     ├─ Append user message and AI response
     ├─ manager.exit_retry_mode()
     ├─ Save chat
     │
     ▼
REPL: Continue
```

## Key Design Principles

1. **Single Responsibility**: Each component has a clear, focused purpose
2. **Separation of Concerns**: UI (REPL) separated from business logic (Orchestrator)
3. **Single Source of Truth**: SessionManager is the only state container
4. **Testability**: Clean interfaces enable comprehensive unit testing
5. **Encapsulation**: State transitions are encapsulated in SessionManager
6. **Signal-Based Communication**: Commands use signals for complex state changes
7. **Action-Based Communication**: Orchestrator uses actions to communicate with REPL

## Future Improvements

1. **Provider Cache Clearing**: Implement cache clearing when timeout changes
2. **Session Persistence**: Save/restore session state across restarts
3. **Async Optimizations**: Parallelize independent operations
4. **Plugin Architecture**: Allow custom AI providers
5. **Streaming UI**: Enhanced progress indicators during streaming
6. **Multi-Session**: Support multiple concurrent chat sessions

## Files Overview

| File | Lines | Purpose |
|------|-------|---------|
| `session_manager.py` | 470 | Session state management |
| `orchestrator.py` | 542 | Orchestration logic |
| `repl.py` | 332 | REPL loop (reduced 42%) |
| `commands/base.py` | 185 | Command base mixin |
| `commands/runtime.py` | 182 | Runtime commands |
| `commands/metadata.py` | 115 | Metadata commands |
| `commands/chat_files.py` | 286 | Chat file commands |
| `commands/misc.py` | 361 | Miscellaneous commands |
| `streaming.py` | 58 | Streaming response handling |
| `ai_runtime.py` | 142 | AI provider runtime |

## Conclusion

The refactoring achieved a cleaner, more maintainable architecture by:

- Eliminating session/session_dict duality via SessionManager
- Extracting orchestration logic to ChatOrchestrator
- Reducing REPL complexity by 42%
- Improving testability (330 tests, all passing)
- Establishing clear component boundaries and responsibilities

This architecture provides a solid foundation for future enhancements while maintaining code quality and testability.
