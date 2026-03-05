# Emojihunt Design Specification

Context: distilled from a design conversation dated 2026-03-06 and organized into a self-contained app specification.

## Purpose

Define the user-facing behavior of `emojihunt`, a one-shot CLI application that scans selected files and directories for emoji usage and produces HTML artifacts for review.

## Scope

This specification covers:
- CLI behavior
- scan target and ignore handling
- emoji classification and danger signaling
- HTML artifact requirements
- relevant path, timestamp, and console-output rules

This specification does not cover:
- implementation libraries or package choices
- internal module layout
- per-file occurrence listings in reports
- automatic recommendation algorithms for replacement suggestions

## Terms

- Catalog: The full HTML inventory of emoji sequences known to the upstream emoji dataset.
- Findings report: The timestamped HTML report of emoji sequences actually found in the scan targets.
- Scan target: A user-provided file or directory selected for scanning.
- Ignore file: A user-provided file containing ignore patterns for files and directories.
- Ambiguous presentation: A sequence that is emoji-capable but defaults to text presentation unless explicitly forced.

## Requirements

### Application Shape

- `emojihunt` MUST be a one-shot CLI application, not a REPL application.
- The application MUST expose an installed CLI entry point named `emojihunt` so users can invoke it by name without a `python ...` wrapper.
- The application MUST support two user-facing operations:
  - generating the full catalog
  - scanning targets and generating a findings report

### CLI Contract

- User-supplied inputs MUST be provided through descriptive long named options.
- User-supplied named options MUST be order-independent.
- Help handling MUST take precedence over normal argument validation.
- Any unrecognized named option MUST halt execution with a visible error.
- The CLI MUST NOT silently discard unexpected extra arguments.
- If boolean flags are introduced later, their presence alone MUST enable them. They MUST NOT require explicit `true` or `false` values.

### Scan Targets and Ignore Behavior

- The scan operation MUST accept one or more scan targets.
- The scan operation MUST accept a destination directory for generated findings reports.
- The scan operation MUST accept an ignore file for file and directory ignore patterns.
- The application MUST also honor `.gitignore` rules during scanning.
- Directory traversal MUST be lazy. The application MUST inspect each directory before entering it and MUST skip ignored directories without first materializing all descendant paths.
- The application MUST support both files and directories as scan targets.

### Path and Filename Rules

- Incoming path text MUST be normalized from NFD to NFC before mapping checks.
- User-supplied paths MUST preserve Unicode safely.
- User-supplied paths containing NUL (`\\0`) MUST be rejected.
- The application MUST never use the current working directory implicitly to map or resolve user-supplied paths.
- Absolute paths MUST be accepted as-is.
- `~`-prefixed paths MUST map to the user home directory.
- Pure relative scan targets, ignore-file paths, and report destinations MUST be rejected unless the application explicitly provides an absolute base directory for resolution.
- Windows rooted-but-not-fully-qualified forms such as `\\temp` and `C:temp` MUST be rejected.
- Dot segments (`.` and `..`) MUST be resolved only after mapping onto an explicit absolute context.
- Forward-slash and backward-slash input styles SHOULD both be accepted.
- Repeated path separators SHOULD be accepted.
- Full user-supplied paths MUST be treated as paths. Filename-segment sanitization rules MUST NOT be applied to an entire path string.
- When the application generates timestamped filenames, it MUST use underscores to separate semantic groups and SHOULD use hyphens inside the time group.

### Emoji Classification

- Emoji findings MUST be classified as full sequences, not as isolated single code points when selectors, joiners, or modifiers are present.
- Broad code point range checks alone MUST NOT be treated as sufficient for emoji classification.
- The application MUST classify dangerous or fragile emoji usage for review.

### Danger Model

- Danger signaling in HTML MUST use only:
  - red for immediate action
  - yellow for caution
  - no special highlight for all other entries
- The application MUST NOT use green "safe" highlighting.
- Red MUST apply when:
  - the emoji sequence contains a variation selector
  - the emoji sequence has ambiguous or text-default presentation
- Yellow MUST apply when:
  - the emoji sequence contains a zero width joiner
  - the emoji sequence contains a skin tone modifier
  - the emoji sequence was introduced in Unicode 14.0 or later
- If an entry matches both red and yellow conditions, red MUST win visually and all triggered reasons SHOULD still be listed.

### Catalog

- The catalog MUST be generated as HTML.
- The catalog MUST be organized as a reviewable HTML table.
- The catalog MUST contain the complete upstream emoji dataset known to the application.
- The catalog MUST help users review dangerous findings and manually look up visually or semantically similar alternatives.
- The catalog MUST use a single deterministic ordering based on the canonical full code point sequence in ascending order so that diffs show only actual data changes.
- The catalog MUST include, at minimum:
  - rendered emoji sequence
  - human-readable name
  - canonical code point sequence
  - Unicode version introduced
  - presentation default or ambiguity status
  - sequence-structure attributes needed for review, including whether the sequence contains a variation selector, a zero width joiner, and a skin tone modifier
  - risk level
  - risk reason list
  - semantic group or category when the upstream dataset exposes one
- The catalog SHOULD include every additional stable, non-location-specific Unicode or emoji attribute that is available from the chosen upstream dataset and helps human review.

### Findings Report

- The findings report MUST be generated as HTML.
- The findings report MUST be timestamped.
- The findings report MUST aggregate by unique emoji sequence and occurrence count.
- The findings report MUST NOT include per-occurrence file locations.
- The findings report MUST include, at minimum:
  - all catalog fields
  - occurrence count
- The findings report MUST use a deterministic review order:
  - red entries first
  - yellow entries second
  - unhighlighted entries last
  - within the same risk level, higher occurrence counts first
  - remaining ties broken by canonical full code point sequence in ascending order

### HTML Formatting

- HTML output MUST prioritize human review and diff readability over compactness.
- Regular, pretty-printed HTML is required. Minified HTML is prohibited.
- A data row SHOULD be written across multiple lines so a diff can isolate the changed cell or cells.
- Risk state MUST be conveyed through row or cell background color, not through icon markers.

### Timestamps

- Timestamped findings-report filenames SHOULD follow the pattern `YYYY-MM-DD_HH-MM-SS_<semantic-group>.html`.
- User-facing timestamps shown inside the HTML SHOULD default to local time.
- User-facing timestamps SHOULD omit timezone markers unless a specific need for disambiguation exists.
- Any machine-oriented timestamp emitted in artifact metadata or logs MUST use UTC, high precision, and an explicit UTC marker, and any corresponding variable or key name MUST include `utc`.

### Runtime Console Output

- Runtime console output MUST follow the single-spacing rule: each output segment emits exactly one leading empty line except the first segment, and no segment emits a trailing empty line.
- Runtime console output MUST default to plain text.
- Console output MUST rely on whitespace, headings, and alignment rather than color or decoration.
- Consecutive warnings or errors about the same operation MUST be emitted as a single segment with no blank lines inside that segment.
- The CLI MUST print explicit empty-state feedback when there is nothing to report.
- If a summary block uses `key: value` lines, values MUST start at the same column across the entire block.
- Runtime console output MUST NOT be hard-wrapped to a fixed width.

## Decision Tables

### User-Facing Operations

| Operation | Inputs | Primary output |
|---|---|---|
| Generate catalog | Output file path | Full HTML catalog |
| Scan targets | One or more targets, findings-report destination directory, optional ignore file | Timestamped HTML findings report |

### Danger Classification

| Condition | Highlight | Why it matters |
|---|---|---|
| Variation selector present | Red | Presentation override may not render reliably |
| Ambiguous or text-default presentation | Red | Appearance depends on fonts and renderers |
| Zero width joiner present | Yellow | Joined rendering may fragment |
| Skin tone modifier present | Yellow | Modifier support may fragment or fall back poorly |
| Unicode 14.0 or later | Yellow | Newer emojis may not render on older systems |

### Artifact Requirements

| Artifact | Deterministic order | Timestamped | Includes Unicode version | Review ordering |
|---|---|---|---|---|
| Catalog | Canonical full code point sequence ascending | No | Yes | Supports manual lookup of similar alternatives through visible metadata |
| Findings report | Risk severity, then occurrence count descending, then canonical full code point sequence ascending | Yes | Yes | Surfaces dangerous and common entries first |

## Conformance Examples

Example findings-report filename:

```text
2026-03-06_14-22-18_emoji-findings.html
```

Example diff-friendly HTML row:

```html
<tr class="risk-red">
  <td class="emoji">⚡️</td>
  <td class="code-points">U+26A1 U+FE0F</td>
  <td class="unicode-version">4.0</td>
  <td class="risk-level">red</td>
  <td class="risk-reasons">variation selector</td>
  <td class="occurrence-count">3</td>
</tr>
```

Example empty-state console output:

```text
No emoji findings.
```

## Out of Scope

- REPL behavior
- Per-file finding locations in the HTML report
- Automatic selection of replacement emojis
- Specific parser, HTML, or Unicode libraries

## Open Questions

- What are the exact CLI option names for the two user-facing operations?
