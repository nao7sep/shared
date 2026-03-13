# Constants and Named Values

Context: distilled from a conversation on 2026-03-13 about when to extract literals into named constants and when to leave them inline.

## Purpose

Define language-agnostic rules for deciding whether a literal value should be extracted into a named constant, and where that constant should live. The goal is to eliminate genuinely magic values without over-engineering every literal into an indirection.

## Scope

Covers:
- Extraction criteria for string and numeric literals
- Inline-acceptable categories
- Constant placement and naming
- Anti-patterns to reject

Does not cover language-specific constant mechanisms (e.g., `enum`, `const`, `final`, `frozen`), configuration file formats, or runtime feature flags.

## Applicability

This specification is language-agnostic in intent. Code examples and library references use Python for concreteness, but all behavioral rules apply equally to any implementation language. When working in a different ecosystem, substitute equivalent libraries and idioms — the rules describe *what* the code must do, not *which package* does it.

## Terms

- Magic value: A literal whose meaning, origin, or reason for its specific value is not obvious at the usage site.
- Named constant: A module-level or class-level binding with an `UPPER_SNAKE_CASE` name that gives a literal a semantic identity.
- Contract value: A literal that forms part of an interface between systems or layers (environment variable names, config keys, API route paths, HTTP header names, database identifiers in raw queries).

## Requirements

### Extraction Criteria

A literal MUST be extracted into a named constant when ANY of the following conditions is true:

1. **Duplication.** The same literal appears in two or more locations.
2. **Non-obvious meaning.** A reader would need external context to understand the value's purpose or derivation (e.g., `86400` as seconds-in-a-day, a regex pattern, a domain-specific threshold).
3. **System boundary or contract.** The value is a coupling point with an external system or a cross-layer interface where a typo would fail silently.
4. **Tunable policy.** The value represents a decision that is likely to change independently of the surrounding logic (rate limits, retry counts, default page sizes, expiry durations), even if currently used in only one location.

### Inline-Acceptable Categories

A literal SHOULD remain inline when ALL of the following are true:

- It is used in exactly one location.
- Its meaning is unambiguous in context.
- It does not fall under any extraction criterion above.

The following categories are presumed inline-acceptable unless an extraction criterion overrides them:

| Category | Examples | Rationale |
|---|---|---|
| Arithmetic identity and boundary values | `0`, `1`, `-1` | Universally understood primitives |
| Initialization defaults | `""`, `[]`, `{}`, `None`, `True`, `False` | Language primitives with no hidden meaning |
| Format strings and log messages | `f"User {name} created"`, `"No items found."` | The message is its own documentation |
| Test expectations | `assert result == 42` | Tests should read as specifications |
| Self-documenting small values in context | `max_retries=3`, `indent=2`, `timeout=30` | Meaning and unit are clear from the parameter name and surrounding code |
| Single-site branching values | `if status == "pending"` in one function | No duplication, no cross-layer contract |

### Constant Placement

- Constants MUST live in the module that owns the concept. A database module owns its table name constants; an auth module owns its token lifetime constants.
- A shared constants module is justified ONLY when the value genuinely crosses layer boundaries (e.g., an application name used in both CLI output and filesystem paths).
- Related constants SHOULD be grouped together in a cohesive block, not scattered across a flat alphabetical list.

### Naming

- Module-level constants MUST use `UPPER_SNAKE_CASE`.
- The name MUST include the unit when the type alone does not convey it (e.g., `TIMEOUT_SECONDS`, `MAX_SIZE_BYTES`, `RETRY_DELAY_MS`).
- The name MUST convey intent, not just the value (e.g., `SESSION_EXPIRY_SECONDS`, not `EIGHTY_SIX_THOUSAND_FOUR_HUNDRED`).

## Decision Table

| Condition | Action |
|---|---|
| Used in 2+ locations | Extract |
| Used once, meaning non-obvious | Extract |
| Contract value (env var name, API path, config key, DB identifier) | Extract |
| Tunable policy value (limit, threshold, default size) | Extract |
| Used once, obvious in context, not a contract or policy | Inline |
| Test assertion value | Inline |
| Format string or log message | Inline |
| Language primitive (`0`, `""`, `None`, `True`) | Inline |

## Anti-Patterns

| Anti-pattern | Description |
|---|---|
| Constants cathedral | A single shared file with hundreds of named values imported everywhere, creating a false dependency hub |
| Single-use extraction | `COLON_SEPARATOR = ":"` or `DEFAULT_GREETING = "Hello"` — adds indirection without clarity |
| Wrapping language primitives | `HTTP_OK = 200`, `EMPTY_LIST = []`, `NEWLINE = "\n"` — universally understood values that gain nothing from naming |
| Linter-driven extraction | Creating a meaningless constant solely to silence a "magic number" warning when the value is self-documenting in context; suppress the warning instead |

## Conformance Examples

Extract — non-obvious meaning, used once:
```
SESSION_EXPIRY_SECONDS = 86400
# ...
token = create_token(expires_in=SESSION_EXPIRY_SECONDS)
```

Extract — contract value:
```
ENV_API_KEY = "MYAPP_API_KEY"
# ...
api_key = os.environ[ENV_API_KEY]
```

Extract — duplicated value:
```
DEFAULT_PAGE_SIZE = 25
# used in list_users(), list_orders(), and the CLI help text
```

Inline — self-documenting in context:
```python
response = fetch(url, timeout=30)
```

Inline — test expectation:
```python
assert calculate_tax(100) == 8.5
```

Inline — format string:
```python
print(f"Processed {count} file(s) in {elapsed:.1f}s")
```

Inline — single-site branch:
```python
if task.status == "pending":
    schedule(task)
```

## Out of Scope

- Language-specific constant mechanisms (`enum`, `const`, `final`, `frozen`, compile-time constants).
- Runtime configuration systems, feature flags, or environment variable loading strategies.
- Build-time code generation for constants.
- Internationalization and string localization.

## Open Questions

- Whether contract values that appear exactly once (e.g., a single environment variable read) should be extracted at the call site or at the top of the module is a judgment call not fully resolved. The spec requires extraction but does not mandate placement within the file.
- Whether linter magic-number rules should be globally configured to exempt common values (0, 1, -1, 2) or handled with per-site suppression is left to project-level tooling decisions.
