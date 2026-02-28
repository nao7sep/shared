# Review: commit `843cf369b646ef3f77aac1683dd60cdb83d46359` (`apps/polychat`)

## Scope

- Reviewed only `apps/polychat` changes from commit `843cf369b646ef3f77aac1683dd60cdb83d46359`.
- Focused on source code paths with runtime impact and public API impact.
- Skipped markdown/data content except for the required review recipe and playbook loaded before the review.

## Findings

### 1. Title/summary generation now includes `error` messages in helper-AI context

- Severity: medium
- Files:
  - `/Users/nao7sep/code/shared/apps/polychat/src/polychat/commands/meta_generation.py:67`
  - `/Users/nao7sep/code/shared/apps/polychat/src/polychat/commands/meta_generation.py:128`
  - `/Users/nao7sep/code/shared/apps/polychat/src/polychat/formatting/history.py:22`

Before this commit, `generate_title()` and `generate_summary()` called `get_messages_for_ai(chat_data)`, which intentionally filtered the chat down to `user` and `assistant` turns. This commit replaced that with `format_for_ai_context(chat_data.messages)`, and `format_for_ai_context()` formats every `ChatMessage` role it is given, including `error`.

That changes user-visible behavior after a failed request. A chat that ends in an error now feeds helper AI the provider failure text instead of only the conversation history, so `/title` and `/summary` can be generated from error strings like timeouts/auth failures rather than the actual chat content. In the degenerate case where the chat contains only an `error` message, the old code returned "No messages in chat to generate title/summary from"; the new code generates metadata from the failure text instead.

Recommended fix: restore the old filtering boundary for title/summary generation, either by calling `get_messages_for_ai(chat_data)` again or by explicitly filtering `chat_data.messages` to `role in {"user", "assistant"}` before formatting. Add regression coverage for chats with trailing `error` messages and for chats containing only an `error`.

### 2. `SessionManager.to_dict()` no longer returns a plain/serializable diagnostic dictionary

- Severity: medium
- Files:
  - `/Users/nao7sep/code/shared/apps/polychat/src/polychat/session_manager.py:127`
  - `/Users/nao7sep/code/shared/apps/polychat/src/polychat/session/accessors.py:66`

`SessionManager.to_dict()` still advertises "a plain dictionary for diagnostics and tests", but the new `state_to_dict()` implementation now returns live `RuntimeProfile` and `ChatDocument` objects under `"profile"` and `"chat"` instead of serialized dictionaries.

That is a compatibility break for any diagnostic/test/tooling code that consumes `to_dict()` as a nested dict tree or JSON-serializable snapshot. I validated the current implementation with a minimal runtime check against `state_to_dict(...)`; `json.dumps(...)` now fails with `TypeError: Object of type RuntimeProfile is not JSON serializable`.

Recommended fix: serialize nested models at this boundary (`state.profile.to_dict()` and `state.chat.to_dict(...)`) or rename the API if the intent is to return the live object graph instead of a plain diagnostic snapshot.

## Validation Notes

- Review method: static diff review of the commit, plus small runtime checks against the current `polychat` source tree to validate the two behaviors above.
- I did not run commit-scoped test suites against the historical revision itself.
