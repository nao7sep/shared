# Viber

Implementation plan generated from conversation on 2026-02-26.

## Overview
Viber is a local Python REPL app for managing repeated cross-project maintenance tasks. Users define project groups, register projects (one group per project), add tasks that apply to one group or all groups, and track per-project task assignments as `pending`, `ok`, or `nah`. The tool also optionally generates per-group HTML check pages so users can quickly see maintenance state across many projects.

## Requirements

### Core Domain and Lifecycle
- Define first-class entities: `Group`, `Project`, `Task`, `Assignment`.
- Support CRUD for groups, projects, and tasks.
- Each project belongs to exactly one group.
- Project states are `active`, `suspended`, `deprecated`.
- Task includes description, UTC creation timestamp, and optional target group (or all groups when unset).
- Creating a task must immediately generate `pending` assignments for matching `active` projects only.
- Assignments must not be backfilled for tasks created before project registration, during project suspension, or after deprecation.
- Deleting a project or task must cascade-delete related assignments.
- Deleting a group must be blocked if any project references it.

### IDs, Data Integrity, and Storage
- Use integer IDs for groups, projects, and tasks.
- IDs are 1-based (start from `1`) and increment predictably.
- Store all state in a single JSON file (`--data`) as a relational-style structure.
- Preserve JSON structure stability for diff-friendly reviews.
- Assignment lookup must be efficient for large tables (dictionary-style key access, not list scanning).
- Assignment identity is by `(project_id, task_id)` pair (composite relationship).

### Assignment Resolution and Comments
- Assignment statuses are `pending`, `ok`, `nah`.
- `ok` and `nah` commands must work with either token order (`pX tY` or `tY pX`).
- Resolution flow is interactive: show target details, confirm, then prompt optional comment.
- Comments are supported for both `ok` and `nah`.

### REPL and Command Behavior
- REPL is the primary interface.
- Two work scopes are required:
- Project scope: process pending tasks for one project.
- Task scope: process projects pending one task.
- `view`/`v` without arguments shows all pending assignments.
- If no pending assignments exist, show an explicit completion message.
- `view p<ID>` shows pending tasks for one project.
- `view t<ID>` shows projects pending one task.
- `read`/listing commands must include deprecated projects so CRUD can still target them.
- `view` must exclude deprecated projects.
- Provide full-word commands and one-letter aliases.
- Full-word commands must be primary in help/docs; aliases are secondary.
- Include REPL `help`.
- Include both `exit` and `quit` (full words only) to leave REPL.
- Include `--help` for CLI startup; when present, ignore all other CLI parameters.

### CLI Options and Path Handling
- Use `--data` for JSON state file path (default discussed: `data.json`).
- Use `--check` for optional HTML output base path (default discussed: `check.html`).
- If `--check` is provided, regenerate HTML outputs after each state mutation.
- Relative/aliased path handling must follow shared path-mapping rules:
- No CWD-dependent resolution.
- Support `~` (home) and `@` (app root).
- Require explicit absolute base context for pure relative inputs.
- Reject invalid rooted-relative Windows forms and NUL-containing input.

### HTML Check Output
- Split output into one file per group using the base path stem (example: `check.html` -> `check-<group>.html`).
- Render tasks as rows (newest first) and projects as columns.
- Show suspended projects in HTML.
- Hide deprecated projects in HTML.
- Render no-assignment lifecycle gaps as blank cells.
- Use visually distinct status marks for resolved states (`ok` vs `nah`), with pending clearly distinguishable.

### Timestamp and CLI Output Conventions
- Internal timestamps must be UTC, high precision, and explicit UTC format.
- UTC fields should include `utc` in key names.
- User-facing timestamps default to local-time display without timezone suffix unless requested.
- CLI output should follow shared formatting standards:
- Plain-text-first output.
- Exactly one blank line between semantic segments.
- Explicit empty-state feedback.
- Complex blocks isolated from prompts/status lines.

### Naming and Product Identity
- App name is fixed as `viber`.
- Purpose: maintain vibe-coding speed and quality with minimal overhead for repetitive maintenance checks.

## Architecture
- **Data Models (Pydantic):** typed models for `Group`, `Project`, `Task`, `Assignment`, and root database model.
- **State Store:** load/save one JSON state file, preserve stable structure, manage 1-based ID allocation.
- **Domain Service Layer:** enforce lifecycle rules, assignment generation, state transitions, and cascading deletes.
- **Query Layer:** provide pending views (`all`, by project, by task) with state filtering rules.
- **REPL Layer:** parse full commands + aliases, run interactive flows (`ok`/`nah` confirm + comment, work loops, help, safe exit).
- **Path Layer:** centralized path mapping/validation compliant with shared path spec.
- **HTML Renderer:** generate per-group check pages; use constant-time assignment lookup keyed by project/task composite identity.
- **CLI Output Formatter:** apply shared CLI output spacing/empty-state conventions.

## Implementation Steps
1. Define typed domain models and enums/constants for project states and assignment statuses.
2. Design and implement the JSON database schema with 1-based integer ID allocation and composite assignment identity.
3. Implement state store load/save behavior with deterministic, diff-stable serialization.
4. Implement path parsing/mapping utilities aligned with the shared path-mapping specification.
5. Implement group/project/task CRUD services, including foreign-key validation and blocked group deletion when referenced.
6. Implement task creation logic that generates assignments only for currently active, matching projects.
7. Implement project lifecycle transition logic (`active`, `suspended`, `deprecated`) and enforce assignment generation rules.
8. Implement assignment resolution flows (`ok`, `nah`) with confirmation and optional comment capture.
9. Implement pending query methods for `view` modes (`all`, project-scoped, task-scoped) and deprecated filtering.
10. Implement REPL command grammar with full-word commands first and single-letter aliases, including `help`, `exit`, and `quit`.
11. Implement work-loop command (`work`/`w`) for project/task iterative processing with skip/quit controls.
12. Implement HTML renderer that writes per-group files from `--check`, handles blank lifecycle cells, and excludes deprecated projects.
13. Integrate mutation hooks so every state-changing command refreshes HTML outputs when `--check` is configured.
14. Implement CLI startup argument handling for `--data`, `--check`, and `--help` short-circuit behavior.
15. Add tests covering lifecycle edge cases, CRUD constraints, assignment lookup correctness, CLI/repl flows, and renderer behavior.
16. Write README/help docs with full-word command examples first, alias forms second, and file-path usage examples.

## Open Questions
- Confirm whether `--check` should always default to `check.html` when omitted, or stay disabled unless explicitly set.
- Confirm exact no-pending message text for `view`/`v`.
- Confirm whether suspended projects should be excluded from actionable `view` output in all cases, or only deprecated projects should be excluded.
- Confirm exact display symbols for `pending`, `ok`, and `nah` in HTML (emoji/text variants).
- Confirm whether task update should allow changing target group, or only description.
- Confirm final constraints for uniqueness/casing of group and project names.
