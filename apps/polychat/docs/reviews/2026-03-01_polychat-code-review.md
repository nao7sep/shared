# PolyChat Code Review

Date: 2026-03-01

Scope: `src/polychat`

Verification:
- `uv run pytest -q` (`606 passed, 3 deselected`)

## Findings

### 1. Failed sends discard the original prompt, so `/retry` cannot rerun "the same message"

Severity: High

The current error path removes the trailing user message before persisting the error. In [`src/polychat/orchestration/response_handlers.py`](/Users/nao7sep/code/shared/apps/polychat/src/polychat/orchestration/response_handlers.py#L183), `handle_ai_error()` pops the last user turn at lines 209-210 and then saves only an error message at lines 212-220. After that, [`src/polychat/chat/messages.py`](/Users/nao7sep/code/shared/apps/polychat/src/polychat/chat/messages.py#L74) builds retry context from the remaining `user`/`assistant` messages only, so a trailing error no longer carries the failed prompt. Entering retry mode therefore restores the prior context without the failed user message, and [`src/polychat/orchestration/message_entry.py`](/Users/nao7sep/code/shared/apps/polychat/src/polychat/orchestration/message_entry.py#L91) requires the operator to type a fresh `user_input` for the retry attempt.

That behavior contradicts the user guidance in [`src/polychat/session/state.py`](/Users/nao7sep/code/shared/apps/polychat/src/polychat/session/state.py#L134), which says `/retry` will "rerun the same message." In practice, any normal-mode provider failure loses that message, so `/retry` becomes "ask again manually" instead of "retry last interaction." This breaks the advertised recovery flow exactly when the user needs it most.

Recommended direction:
- Preserve the failed user turn alongside the error, or
- Store the failed prompt in retry/error state and seed retry mode from that preserved value.

Remediation plan:
1. Decide whether the failed user turn should remain in chat history or live only in retry metadata.
2. Update the normal-mode error path to preserve enough state for `/retry` to resend the failed prompt automatically.
3. Add coverage for "send fails -> `/retry` resends same prompt" at the orchestration level.

### 2. Mutating commands are not transactional with persistence

Severity: Medium

Several command handlers mutate in-memory chat state before persistence happens. For example, [`src/polychat/commands/runtime_mutation.py`](/Users/nao7sep/code/shared/apps/polychat/src/polychat/commands/runtime_mutation.py#L21) removes messages and hex IDs during `/rewind` and `/purge` before returning a success string. Metadata commands do the same through [`src/polychat/commands/base.py`](/Users/nao7sep/code/shared/apps/polychat/src/polychat/commands/base.py#L86), whose `_update_metadata_and_save()` helper updates metadata but does not save anything despite its name. Persistence is deferred to [`src/polychat/orchestration/signals.py`](/Users/nao7sep/code/shared/apps/polychat/src/polychat/orchestration/signals.py#L195), where `_persist_chat_after_command()` saves after the command result has already been produced.

If `save_current_chat()` fails at that final step (disk full, permissions, transient I/O failure), the user sees an error, but the live session has already been mutated. The chat on disk and the chat in memory then diverge until some later save happens to succeed, which can make a failed command appear to "come back" unexpectedly. This is a correctness problem, not just a UX issue, because subsequent commands operate on state the user was told did not persist.

Recommended direction:
- Perform command-side mutations on a copy and commit them only after a successful save, or
- Move persistence into the mutating command path so each operation can fail atomically.

Remediation plan:
1. Identify all command handlers that mutate `manager.chat` or metadata before save (`/rewind`, `/purge`, `/title`, `/summary`, and similar paths).
2. Refactor one path to use copy-then-commit or explicit in-command persistence, then apply the same pattern consistently.
3. Add failure-path tests that force `save_current_chat()` to raise and verify that in-memory state remains unchanged.
