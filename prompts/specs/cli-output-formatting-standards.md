# CLI Output Formatting Standards

Context: distilled from conversations on February 25 and 28, 2026 about reusable CLI output conventions.

## Purpose

Define a simple, reusable standard for interactive CLI output that stays readable across terminal environments without adding styling complexity.

## Scope

This specification covers runtime console output formatting for interactive CLI apps:
- segment identification and boundaries
- whitespace and spacing
- prompt/output grouping
- optional use of borders and text styling

This specification does not define implementation details, libraries, or language-specific APIs.

## Terms

- Segment: A discrete unit of output with a single purpose. See the segment catalog below for the exhaustive list of segment types.
- Prompt line: A line where the app waits for user input.

## The Single Spacing Rule

Every segment MUST emit exactly one leading empty line before its first content line, with two exceptions:

1. The initial app banner (the very first output after the process starts) MUST NOT emit a leading empty line. The shell prompt above provides sufficient separation.
2. The final segment MUST NOT emit a trailing empty line after its last content line. The shell prompt below provides sufficient separation.

No segment ever emits a trailing empty line. The blank line between any two segments always belongs to the later one.

### Rationale

A segment always knows when it starts but does not always know when it ends. Exceptions, early returns, interrupts, and conditional branches can cut a segment short. If trailing blanks were required, a crash or bail-out would leave the next segment visually glued to the wreckage. Leading-only is resilient by default: the next segment always cleans up.

## Segment Catalog

The following is the exhaustive list of recognized segment types. Every block of output produced by a CLI app MUST be classifiable as one of these. If new output patterns emerge, this catalog should be extended rather than handled ad hoc.

| Segment type | Description | Example |
|---|---|---|
| Banner | App name, version, startup summary. Always first. | `revzip` / `Loaded parameters: ...` |
| Prompt | A line that waits for user input. | `autopage> ` / `Select option: ` |
| Result | Direct output from a command or operation. | `Captured 10 page(s): 1–10.` |
| List | One or more rows of homogeneous items. | Snapshot list, task list, file list. |
| Summary with list | A header line followed by homogeneous rows. | `Available snapshots:` + numbered rows. |
| Confirmation dialog | A question, optional context lines, and user input. | `Type yes to restore:` |
| Warning | A non-fatal advisory message. | `WARNING: Skipped symlink: ...` |
| Error | A failure message. | `ERROR: File not found.` |
| Progress | Incremental status updates (may use `\r` on TTY). | `Scanned: 12 dirs \| 84 files` |
| Empty-state feedback | Explicit message when there is nothing to show. | `No pending tasks.` |
| Farewell | Final message before the process exits. | `Exiting.` |

### Prompt and result grouping

A prompt and its immediate result form a tight visual unit. The result lines appear directly after the prompt line with no blank line between them. The next segment's leading blank provides separation afterward.

### Consecutive warnings or errors

Multiple warnings or errors about the same operation are a single segment. Do not insert blank lines between them.

## Additional Requirements

### Design Defaults

- MUST prioritize simplicity and maintainability over terminal aesthetics.
- MUST default to plain text output.
- MUST rely on structure (whitespace, indentation, and clear symbols) as the primary readability mechanism.

### Empty-State Feedback

- MUST print explicit empty-state feedback when there is nothing to show.
- MUST only show follow-up selection prompts when there is something selectable.

### Borders and Dividers

- SHOULD avoid heavy border usage when spacing and headings are sufficient.
- MAY use borders/dividers when a project explicitly wants them.
- IF borders are used, each border line MUST be exactly 80 characters wide.

### Colors and Text Decorations

- MUST NOT use colors or text decorations by default.
- MAY use color/decorations only when explicitly requested by the developer.
- IF enabled, color/styling MUST be supplementary; meaning must still be clear in plain text.

### Line Length and Wrapping

- MUST NOT hard-wrap runtime console output to a fixed column width.
- MUST rely on terminal word-wrapping behavior for long output lines.
- MUST treat runtime output width policy separately from source-code line-length rules.

## Conformance Examples

One-shot command with no results:
```text
No items to show.
```

One-shot command with results (summary + list):
```text
Found 3 active users:
ID    NAME        ROLE
1     admin       owner
2     alice       editor
3     bob         viewer
```

Interactive REPL with banner, prompt/result pairs, and farewell:
```text
myapp v1.0

> list
No items to show.

> add Buy milk
Added task 1.

> list
1. Buy milk

> exit
Exiting.
```

Warnings followed by an empty-state message:
```text
WARNING: invalid-meta.json: Invalid metadata JSON
WARNING: orphan-data.json: Missing corresponding zip

No valid snapshots available for extraction.
```

Setup flow with multiple prompt segments:
```text
Detected 1 screen(s). Select a capture region:
  1. Entire screen  (2560x1600 at 0,0)
  2. Left half  (1280x1600 at 0,0)
Region [1–2]: 1

Running user applications:
  1. Books  (PID 1234)
  2. Preview  (PID 5678)
Application [1–2]: 1
```

## Out of Scope

- Mandatory graceful interrupt handling/output cleanup for Ctrl+C.
- Forced wrapping of output text at 80 columns.
- GUI-like visual control goals for CLI apps.
- Language- or framework-specific styling/output libraries.
