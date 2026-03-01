# Retry And Secret Modes

Date: 2026-03-01

Status: Intended product behavior clarified on 2026-03-01. This document is the architecture reference for `/retry` and `/secret`.

## Purpose

PolyChat has two special conversation modes that are intentionally not the same:

- `/retry` is a temporary replacement branch for the last interaction.
- `/secret` is a temporary continuation branch after the current committed chat.

Both modes are ephemeral. They exist to let the user explore alternatives without immediately changing the committed chat history on disk.

## Terms

### Committed History

The committed history is the normal chat transcript stored in memory and persisted to file.

Example:

```text
u1, a1, u2, a2
```

This means:

- pair 1 is `u1, a1`
- pair 2 is `u2, a2`

### Interaction Numbering

PolyChat is a chat app, so the logical unit of history is the pair number.

Normal case:

```text
u1, a1, u2, a2, u3, a3
```

Exceptional cases:

```text
u1, a1, u2, e2
```

or:

```text
u1, a1, u2, a2, e3
```

`u2, e2` means the second interaction started with a real user message, but the assistant side failed and the failure was logged as part of that interaction.

`e3` means the third interaction failed before a durable user message was committed as `u3`.

So the model is:

- usually, an interaction is a user/assistant pair
- a failed interaction may also be a durable user/error pair
- exceptionally, the last interaction may instead be a standalone trailing error

So there are three valid last-interaction shapes in the intended model:

- trailing `user + assistant`
- trailing `user + error`
- standalone trailing `error`

## Mode Summary

### `/retry`

`/retry` is for replacing the last interaction.

It branches from the committed chat state immediately before the interaction being replaced, lets the user generate one or more alternative pairs, and then optionally applies one of them to committed history.

### `/secret`

`/secret` is for continuing the conversation off the record.

It branches from the current committed chat, allows a temporary sub-conversation to continue for multiple turns, and discards that entire branch when secret mode ends.

## Retry Mode

### Mental Model

Retry mode asks:

"What if the last interaction had gone differently?"

It does not ask:

"What if we continued the chat after the last interaction?"

The target is the current last interaction only, where the last interaction may be:

- a trailing `user + assistant` pair
- a trailing `user + error` pair
- a standalone trailing `error`

### Entering Retry Mode

If committed history is:

```text
u1, a1, u2, a2, u3, a3
```

then `/retry` targets pair 3.

The AI context used for retry attempts is the committed prefix before that pair:

```text
u1, a1, u2, a2
```

The original `u3, a3` are not sent to the AI during retry attempts.

If committed history is:

```text
u1, a1, u2, e2
```

then `/retry` targets interaction 2.

The AI context used for retry attempts is the committed prefix before that interaction:

```text
u1, a1
```

The original `u2, e2` are not sent to the AI during retry attempts.

If committed history is:

```text
u1, a1, u2, a2, e3
```

then `/retry` targets interaction 3, and the committed prefix is still:

```text
u1, a1, u2, a2
```

The trailing `e3` is not sent to the AI during retry attempts.

### Retry Attempts

Each retry attempt is a hypothetical replacement for the target interaction.

If the committed prefix is:

```text
u1, a1, u2, a2
```

and the user types a new retry prompt:

```text
retry-u3a
```

then the AI receives:

```text
u1, a1, u2, a2, retry-u3a
```

and returns a candidate assistant response:

```text
retry-a3a
```

That produces one candidate pair:

```text
retry-u3a, retry-a3a
```

The user may then type another new retry prompt:

```text
retry-u3b
```

which produces another candidate pair:

```text
retry-u3b, retry-a3b
```

Important properties:

- retry attempts are not written into committed chat history
- retry attempts may use different user prompts from the original
- multiple retry attempts may be created before the user chooses one
- the committed history remains unchanged until `/apply`

### Applying Retry

Applying a retry means:

- remove the current last interaction from committed history
- insert the chosen candidate pair in its place

Example 1: replacing a normal last pair

Before:

```text
u1, a1, u2, a2, u3, a3
```

Chosen candidate:

```text
retry-u3b, retry-a3b
```

After `/apply`:

```text
u1, a1, u2, a2, retry-u3b, retry-a3b
```

Example 2: replacing a durable user/error pair

Before:

```text
u1, a1, u2, e2
```

Chosen candidate:

```text
retry-u2b, retry-a2b
```

After `/apply`:

```text
u1, a1, retry-u2b, retry-a2b
```

Example 3: replacing a trailing standalone error

Before:

```text
u1, a1, u2, a2, e3
```

Chosen candidate:

```text
u3, a3
```

After `/apply`:

```text
u1, a1, u2, a2, u3, a3
```

### Cancelling Retry

Cancelling retry means:

- discard all retry attempts
- exit retry mode
- keep committed history exactly as it was

Example:

Before and after `/cancel`:

```text
u1, a1, u2, a2, u3, a3
```

or:

```text
u1, a1, u2, a2, e3
```

### Retry Invariants

Retry mode must obey these rules:

1. The target is always the current last interaction.
2. The AI context for retry attempts contains only committed interactions before the target.
3. The interaction being retried is never sent to the AI during retry attempts.
4. Each retry attempt is a complete candidate replacement interaction.
5. Retry attempts are ephemeral until `/apply`.
6. `/apply` replaces the target interaction atomically.
7. `/cancel` leaves committed history unchanged.

## Secret Mode

### Mental Model

Secret mode asks:

"What if we continue this chat privately for a while, without committing any of it?"

It is not a retry workflow. It does not replace anything. It creates an ephemeral continuation branch after the current committed history.

### Entering Secret Mode

If committed history is:

```text
u1, a1, u2, a2
```

then entering `/secret` creates a secret branch whose base is:

```text
u1, a1, u2, a2
```

### Secret Continuation

Inside secret mode, the secret branch grows turn by turn and is used as context for later secret turns.

Example:

Committed history:

```text
u1, a1, u2, a2
```

Secret turn 1:

- user enters `secret-u3`
- AI receives:

```text
u1, a1, u2, a2, secret-u3
```

- AI returns:

```text
secret-a3
```

Now the secret branch is:

```text
secret-u3, secret-a3
```

Secret turn 2:

- user enters `secret-u4`
- AI receives:

```text
u1, a1, u2, a2, secret-u3, secret-a3, secret-u4
```

- AI returns:

```text
secret-a4
```

Now the secret branch is:

```text
secret-u3, secret-a3, secret-u4, secret-a4
```

This can continue for any number of secret turns.

### Secret Errors

Secret errors belong to the secret branch only.

If a secret turn fails, the failure:

- may be shown to the user
- may influence the current secret branch while secret mode remains active
- must never be written to committed chat history or file

When secret mode ends, all secret messages and secret errors disappear.

### Exiting Secret Mode

Leaving `/secret` discards the entire secret branch.

If committed history was:

```text
u1, a1, u2, a2
```

and the secret branch had accumulated:

```text
secret-u3, secret-a3, secret-u4, secret-a4
```

then after secret mode ends, the visible committed history is still:

```text
u1, a1, u2, a2
```

The next normal message becomes:

```text
u3
```

not `u5`.

### Secret Invariants

Secret mode must obey these rules:

1. The committed history is the base context.
2. Secret turns accumulate within secret mode and are used as context for later secret turns.
3. Secret turns are never appended to committed history.
4. Secret errors are never appended to committed history.
5. Exiting secret mode discards the entire secret branch.
6. Returning to normal mode resumes numbering from the committed history, not from secret turns.

## Contrast Between The Modes

### `/retry`

- branch type: replacement
- branch base: committed history before the last interaction
- branch lifetime: until `/apply` or `/cancel`
- branch output: one chosen candidate pair may replace the last interaction
- persistence: only the chosen applied pair becomes committed

### `/secret`

- branch type: continuation
- branch base: current committed history
- branch lifetime: until secret mode is turned off
- branch output: no secret turn ever becomes committed
- persistence: none

## State Model

### Retry State

Retry mode needs runtime state with these conceptual fields:

- `target_interaction_number`
- `target_kind`
  - `pair`
  - `standalone_error`
- `committed_prefix`
- `candidate_attempts`
- `selected_attempt_id` (only when applying)

Each candidate attempt should contain:

- `candidate_user_text`
- `candidate_assistant_text`
- optional metadata such as citations, model, timing

### Secret State

Secret mode needs runtime state with these conceptual fields:

- `committed_base`
- `secret_transcript`
- `active`

The actual AI context for a secret turn is:

```text
committed_base + secret_transcript + new_secret_user_message
```

## Persistence Rules

### Retry

Persisted immediately:

- nothing about the candidate attempts

Persisted on `/apply`:

- the new committed history after replacement

Persisted on `/cancel`:

- nothing

### Secret

Persisted immediately:

- nothing

Persisted on exit:

- nothing

Persisted after returning to normal mode:

- only new normal-mode messages from that point onward

## Error Handling Requirements

### Retry Errors

Retry-specific failures must not corrupt committed history.

If a retry attempt fails:

- committed history remains unchanged
- retry mode remains active unless the failure invalidates retry state
- previous candidate attempts remain available unless explicitly cleared

### Secret Errors

Secret failures must not leak into committed history.

If a secret turn fails:

- the committed history remains unchanged
- the failure may exist only within secret runtime state
- turning off secret mode clears it

## UI And Wording Requirements

The product wording should reflect the actual semantics.

### Retry Wording

Good wording:

- "Replace the last interaction with a new candidate pair"
- "Generate alternative continuations from before the last interaction"
- "Apply a retry candidate to replace the last interaction"

Avoid wording that implies automatic replay of the previous user prompt when the product actually expects a new retry prompt.

### Secret Wording

Good wording:

- "Continue off the record"
- "Temporary private branch"
- "Secret turns are used for context but never saved"

Avoid wording that implies secret mode is only a one-turn unsaved send.

## Current Implementation Fit

As of 2026-03-01, the current code roughly fits retry mode better than secret mode.

### Retry

The existing retry flow already behaves like a replacement branch in key places:

- it freezes a retry context before the target interaction
- it stores multiple candidate attempts
- it applies a chosen candidate by replacing the target interaction

However, product wording and some older assumptions may still describe retry as rerunning the same message, which is not the intended contract described here.

### Secret

The existing secret flow does not yet fully match this document.

The current implementation behaves closer to:

- "send one off-the-record message against committed history"

than to:

- "maintain a growing off-the-record continuation branch"

To match this architecture, secret mode must preserve an in-memory secret transcript and include it in subsequent secret turns.

## Required Tests

The test suite should explicitly cover the clarified contract.

### Retry Tests

1. Retrying `u3, a3` sends only `u1, a1, u2, a2, new-u3x`.
2. Retrying `u2, e2` sends only `u1, a1, new-u2x`.
3. Multiple retry attempts can be created before apply.
4. Applying a candidate replaces the last committed interaction atomically.
5. Retrying trailing `e3` replaces it with `u3, a3`.
6. Cancelling retry leaves committed history unchanged.

### Secret Tests

1. Secret turn 2 includes secret turn 1 in AI context.
2. Secret assistant messages are never persisted.
3. Secret errors are never persisted.
4. Exiting secret mode clears the secret transcript.
5. The next normal persisted message resumes from committed numbering.

## Bottom Line

The intended product behavior is:

- `/retry` = ephemeral replacement branch for the last interaction
- `/secret` = ephemeral continuation branch after the current committed chat

The key difference is not privacy alone. The key difference is what the branch means:

- retry rewrites the last interaction
- secret explores a future that is never committed
