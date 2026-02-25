# CLI Output Formatting Standards

Context: distilled from a conversation on February 25, 2026 about reusable CLI output conventions.

## Purpose

Define a simple, reusable standard for interactive CLI output that stays readable across terminal environments without adding styling complexity.

## Scope

This specification covers runtime console output formatting for interactive CLI apps:
- prompt/output grouping
- whitespace and segmentation
- handling of simple vs complex output blocks
- optional use of borders and text styling

This specification does not define implementation details, libraries, or language-specific APIs.

## Terms

- Segment: A contiguous output group representing one semantic operation.
- Prompt line: A line where the app waits for user input.
- Complex object: A visually dense block with two or more information types, such as header+rows, parent+child tree lines, or nested structured data.

## Requirements

### 1. Design Defaults

- MUST prioritize simplicity and maintainability over terminal aesthetics.
- MUST default to plain text output.
- MUST rely on structure (whitespace, indentation, and clear symbols) as the primary readability mechanism.

### 2. Segment Spacing

- MUST use exactly one empty line to separate semantic segments.
- MUST NOT emit two or more consecutive empty lines.
- MUST treat the initial app banner (if present) as the only segment that starts without a leading empty line.
- MAY let any later segment emit one leading empty line before its first content line.

### 3. Prompt and Response Flow

- MUST keep command results visually tied to the triggering prompt.
- SHOULD print simple, direct outputs immediately after the triggering prompt line.
- MUST print explicit empty-state feedback when no results exist.
- MUST only show follow-up selection prompts when there is something selectable.

### 4. Complex Object Isolation

- MUST isolate each complex object with one leading and one trailing empty line.
- MUST avoid letting complex objects visually touch surrounding prompts or status lines.
- SHOULD include a short summary line before a complex object when it helps explain what follows.

### 5. Borders and Dividers

- SHOULD avoid heavy border usage when spacing and headings are sufficient.
- MAY use borders/dividers when a project explicitly wants them.
- IF borders are used, each border line MUST be exactly 80 characters wide.

### 6. Colors and Text Decorations

- MUST NOT use colors or text decorations by default.
- MAY use color/decorations only when explicitly requested by the developer.
- IF enabled, color/styling MUST be supplementary; meaning must still be clear in plain text.

### 7. Line Length and Wrapping

- MUST NOT hard-wrap runtime console output to a fixed column width.
- MUST rely on terminal word-wrapping behavior for long output lines.
- MUST treat runtime output width policy separately from source-code line-length rules.

## Decision Tables

| Output type | Leading empty line | Trailing empty line | Notes |
|---|---:|---:|---|
| Initial banner | No | Optional | First output only |
| Standard segment | Yes (one, optional by segment owner) | Usually yes (one, before next prompt/segment) | Never allow double blank lines |
| Simple result list/message | Usually no (directly after prompt) | Yes (one, before next prompt) | Keep cause-and-effect tight |
| Complex object (table/tree/structured block) | Yes (required) | Yes (required) | Isolate visual complexity |
| Border line (if used) | Context-dependent | Context-dependent | Must be fixed width 80 |

## Conformance Examples

```text
> Command: list
No items to show.

> Command:
```

```text
> Command: list_users
Found 3 active users:

ID    NAME        ROLE
1     admin       owner
2     alice       editor
3     bob         viewer

> Command:
```

```text
================================================================================
```

## Out of Scope

- Mandatory graceful interrupt handling/output cleanup for Ctrl+C.
- Forced wrapping of output text at 80 columns.
- GUI-like visual control goals for CLI apps.
- Language- or framework-specific styling/output libraries.

## Open Questions

- Should the default symbol set (for example, prompt and status markers) be standardized in this spec?
- Should border lines be used only for specific milestones (for example, app banner) or remain fully discretionary?
- Should optional color mode define a fixed semantic palette, or remain project-specific when explicitly enabled?
