# CLI and REPL Architecture

Derived from a conversation on 2026-03-01 covering input package selection, command parsing, history management, multiline input, and terminal robustness.

## Purpose

Define the canonical architecture decisions and behavioral requirements for CLI and REPL applications, so that any implementation—regardless of language or framework—produces consistent, predictable, and professional terminal tooling.

## Scope

Covers:
- Package and tool selection for input, output, and storage
- CLI parameter design and parsing rules
- REPL command routing and string interceptor logic
- History management modes
- Multiline input design
- Interrupt and termination handling
- Non-interactive (piped) execution
- Output volume and pagination
- Concurrency safety and credential security

Does not cover application business logic, data models, or network layer design.

## Terms

| Term | Definition |
|------|------------|
| **CLI mode** | Single-execution invocation via terminal command with flags and arguments |
| **REPL mode** | Continuous read-eval-print loop; the application maintains a running prompt |
| **Quick mode** | REPL input mode where `Enter` submits immediately |
| **Compose mode** | REPL input mode where `Enter` inserts a newline; a separate key combination submits |
| **Raw command** | A REPL command whose final argument is an unquoted, arbitrary natural language string |
| **Noise line** | An input string that conveys no meaningful command and must not be saved to history |

---

## Requirements

### 1. Project Lifecycle (YAGNI Rule)

- **Stable, feature-complete apps:** Do not introduce new dependencies solely to modernize the input layer. Apply the minimal fix needed (e.g., conditionally loading a readline-compatible module for escape sequence handling on non-Windows platforms).
- **New apps and the chosen sandbox reference app:** Use the full modern stack defined in this document.
- Designate at most one existing app as the "sandbox reference app" for the full migration. Once migrated, treat it as the canonical template for all future apps.

### 2. Package Selection

#### 2.1 Input

| Use Case | Package |
|----------|---------|
| Single-line terminal input (cross-platform, no escape sequences) | `prompt_toolkit` (`prompt()` function) |
| Full REPL with history and completion | `prompt_toolkit` (`PromptSession`) |
| Confirmations, Y/N prompts, interactive menus, dropdowns | `Questionary` |
| Stable apps with escape sequence fix only | Conditional `readline` import on non-Windows |
| Password / masked input | `Questionary.password()` or `prompt_toolkit.prompt(is_password=True)` |

Hierarchy for simple line input: `prompt_toolkit` > `readline` > raw built-in `input()`.

#### 2.2 Output

- Use `Rich` (`rich.print()`) for all terminal output: text, tables, JSON, error tracebacks.
- Wrap the main REPL loop in `prompt_toolkit.patch_stdout.patch_stdout()` to prevent background threads or async tasks from corrupting the active input line.

#### 2.3 File Storage

- Use `platformdirs.user_data_dir('<AppName>')` to resolve all local state and configuration paths. Never hardcode `~/.app` or `./` relative paths.

#### 2.4 Packaging

- Define the application entry point under `[project.scripts]` in `pyproject.toml`. Users must be able to invoke the app by name without typing `python main.py`.

---

### 3. CLI Parameter Design

#### 3.1 Parameter Types

| Kind | Rule |
|------|------|
| Positional argument | Reserved for the primary operational target (e.g., a filename or entity). Maximum **two** per command. |
| Named option | Used for all other inputs. Strictly order-independent. |
| Boolean flag | A named option with a boolean type. Presence alone enables it; no value assignment (e.g., `--verbose`, not `--verbose=true`). |

#### 3.2 Flag Naming

- Every option must have a descriptive **long flag** (e.g., `--no-history`).
- **Short flags** (e.g., `-f`) are reserved for universally recognized actions or the top three most frequently used, non-destructive execution options.
- Short flags must not be assigned to destructive or complex state-changing operations.

#### 3.3 Composite Identifiers

- Combined alphanumeric identifiers (e.g., `user1`, `project42`) are **prohibited** as single positional arguments.
- Entity references must be split into two separate arguments: `<entity_type: string>` and `<entity_id: integer>` (e.g., `/update user 1`). This enables native type validation.

#### 3.4 Dependency-Free Parsing Rules

When implementing CLI parsing without a framework (e.g., maintaining stable apps), the parser must enforce:

1. **Help precedence:** Check for `-h` or `--help` before enforcing positional parameter counts. A missing required argument must not prevent help text from displaying.
2. **Boolean flag presence:** Flags are `true` when present; `false` when absent. The parser must never expect `--flag=true` or `--flag true`.
3. **Strict rejection:** Any unrecognized named parameter causes an immediate halt with an error message. Silent discard of extra arguments is prohibited.
4. **Type casting at extraction:** Cast positional parameters to their required types (e.g., integer) immediately upon extraction, wrapping in an error handler to catch malformed input before it reaches business logic.

---

### 4. REPL Command Routing

#### 4.1 String Interceptor (Parsing Bifurcation)

Before any command reaches the routing engine, the raw input string must be examined:

1. **Peek at the command verb** (the first whitespace-delimited token).
2. **If the verb is in the `RAW_COMMANDS` whitelist** (commands that accept a natural language payload):
   - Split using a bounded split with `maxsplit = N`, where `N` equals the exact count of strict positional arguments preceding the payload.
   - The final element in the resulting list is the unquoted, multi-word payload.
3. **Otherwise:** Parse using POSIX-compliant shell splitting (equivalent to `shlex.split()`).
   - A parsing error (e.g., unclosed quotation) must be caught and reported to the user as a syntax error. It must not crash the REPL.

#### 4.2 Routing Engine

- A single routing engine (e.g., `Typer`) handles all command definitions, argument validation, type coercion, and help text generation.
- The engine must be invoked with standalone mode disabled so that `--help`, bad arguments, and other exit conditions do not terminate the running REPL process. Expected exit and abort exceptions from the engine must be explicitly caught and suppressed.
- `sys.argv` string parsing and manual routing logic are prohibited in REPL command dispatch.

#### 4.3 Silent Failure Prohibition

- The routing engine must never silently discard unexpected extra arguments. Any command receiving more arguments than it declares must halt and display a validation error visible to the user.

#### 4.4 Sub-Prompts and Confirmations

- Confirmations, selections, and secondary data entry must use `Questionary` or must explicitly pass `add_history=False` (or equivalent) to the input session. This prevents incidental user responses (`y`, `n`, selection values) from polluting the REPL's command history.

---

### 5. History Management

#### 5.1 Default Behavior

- History is **ephemeral by default**: stored in memory for the current session only. No files are written unless the developer explicitly opts in.

#### 5.2 History Modes

| Mode | Behavior |
|------|----------|
| **Disabled** | Up-arrow retrieves nothing. Use a `DummyHistory` backend. |
| **Session-only (default)** | Up-arrow works within the running session; no files written. Use an `InMemoryHistory` backend. |
| **Persistent** | History is saved to disk across sessions. Use a `FileHistory` backend. |

Switching between modes is achieved solely by injecting the appropriate history backend at session initialization. No manual buffer pausing, clearing, or file I/O operations are written in business logic.

#### 5.3 Persistent History Path

When the developer enables file persistence, the default path is:

```
~/.{app-name}/history
```

Resolved using the platform's home directory API. This path may be overridden by the developer.

#### 5.4 Noise Filter

Before appending any input to the history buffer, the string must be stripped of surrounding whitespace and lowercased. If the result matches any of the following, it is **discarded** and not added to history:

`yes`, `y`, `no`, `n`, `quit`, `exit`, `` (empty string)

The noise filter applies to both in-memory and persistent backends.

---

### 6. Multiline Input

#### 6.1 Input Modes

| Mode | `Enter` key behavior | Submission |
|------|---------------------|------------|
| **Quick** | Submits the command immediately | `Enter` |
| **Compose** | Inserts a literal newline | See §6.2 |

Quick mode does not support multiline wrapping.

#### 6.2 Compose Mode Submission Fallbacks

To accommodate terminal emulator fragmentation across macOS (Terminal.app, iTerm2), Linux, and Windows, Compose mode must accept all of the following submission bindings:

| Binding | Notes |
|---------|-------|
| `Alt+Enter` / `Option+Enter` | Primary; used by most CLI agent tools |
| `Esc` then `Enter` | Universal terminal fallback (press and release `Esc`, then press `Enter`) |
| `Ctrl+J` | Line Feed control character fallback |

Custom `Alt`/`Option` bindings must not be the sole submission method.

#### 6.3 UI Labeling

When Compose mode is active, the prompt prefix must explicitly display the submission hotkey (e.g., `Compose (ESC+Enter to submit)> `).

---

### 7. Interrupt and Termination

#### 7.1 `Ctrl+C` (SIGINT) Behavior

`Ctrl+C` is a **context-cancellation action only**. It is permanently prohibited from terminating the application.

| Context | Behavior |
|---------|---------|
| At the main prompt (text being typed) | Clears the current line buffer; returns a fresh prompt |
| Inside a wizard or sub-prompt | Cancels the flow; returns the user to the main REPL prompt |
| During a blocking or async operation | Safely aborts the operation (rolling back if necessary); prints `[Operation Cancelled]`; returns to main prompt |

All three cases must be handled via explicit interrupt catching in the execution layer. An unhandled `Ctrl+C` that propagates to the process level is a defect.

#### 7.2 Application Termination

Graceful shutdown is available only through:
- An explicit built-in command (e.g., `/exit`, `/quit`)
- `Ctrl+D` (EOF signal) when running interactively

---

### 8. Non-Interactive (Piped) Execution

At startup, the application must detect whether it is connected to an interactive terminal.

- **If interactive:** Launch the REPL loop normally.
- **If not interactive (data is being piped in):** Bypass the REPL loop. Read from standard input, execute each command, and exit with a standard POSIX exit code.

Launching a blocking prompt loop when stdin is not a TTY is a defect that causes hangs in automation scripts.

---

### 9. Output Volume and Pagination

Commands expected to return datasets that may exceed the terminal's visible height must paginate their output:

- With `Rich`: use `with console.pager():` around the output block.
- Without `Rich`: detect the terminal height and pause output with a user-visible continuation prompt when the line count exceeds it.

Scrolling thousands of lines of output without pause is a defect.

---

### 10. Security and Credential Handling

1. Any command verb known to accept credentials, tokens, or passwords (e.g., `/login`, `/auth`) must be intercepted **before** its input reaches the history buffer.
2. The history manager must either:
   - Discard the line entirely (same as the noise filter), or
   - Redact the payload (e.g., record `/login ********`).
3. Plain-text secrets must never be written to in-memory history or disk.
4. When prompting for a password mid-flow, use masked input so the terminal does not echo the characters.

---

## Decision Tables

### Which parsing strategy applies to a REPL command?

| Is the command verb in `RAW_COMMANDS`? | Action |
|----------------------------------------|--------|
| Yes | `str.split(' ', maxsplit=N)` where N = number of strict positional args before the payload |
| No | POSIX shell split (equivalent to `shlex.split()`) |

### Which history backend applies?

| Developer intent | Backend |
|-----------------|---------|
| No history at all | `DummyHistory` |
| In-session history only (default) | `InMemoryHistory` |
| Persistent across sessions | `FileHistory` at `~/.{app-name}/history` |

### How is a CLI option categorized?

| Input characteristic | Parameter type |
|---------------------|---------------|
| Primary target, position-dependent, required | Positional argument (max 2) |
| Optional, order-independent, key-value pair | Named option |
| Toggle, no value needed | Boolean named option (flag) |

---

## Out of Scope

- LLM or AI-specific input handling (streaming tokens, multi-turn context management)
- GUI or web-based interfaces
- Protocol-level terminal control (e.g., raw mode, custom VT100 sequences beyond what `prompt_toolkit` abstracts)
- Application business logic, data models, or persistence strategy beyond history file paths

---

## Open Questions

- **Async REPL:** No decision has been made on whether to standardize on `asyncio` for REPL apps that issue network requests. The concurrency trap is documented but the solution (async main loop with `session.prompt_async()`) has not been formally adopted.
- **Dynamic tab-completion:** No standard has been set for completing REPL command arguments (e.g., auto-completing valid entity IDs from a data source) using the `prompt_toolkit` `Completer` API.
- **Output paging threshold:** The exact line count at which pagination must trigger has not been defined. Implementations may use terminal height as a heuristic.
- **`RAW_COMMANDS` registration mechanism:** No standard has been set for how the whitelist is declared or discovered (e.g., decorator, configuration file, explicit set).
- **Multiline input in `prompt_toolkit`:** One app uses `prompt(multiline=True)` for compose-style input. Whether this app's specific key bindings conform to the multiline standard in §6 has not been verified.
