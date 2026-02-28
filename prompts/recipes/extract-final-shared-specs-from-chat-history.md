# Extract Final Shared Specs From Chat History

Distill a chat history file into a language-agnostic shared specification document.

## Scope

Read the chat history source file and extract final decisions, requirements, constraints, and unresolved questions.

Focus on specification-level behavior (`WHAT`), not implementation details (`HOW`).

Skip code snippets, library-specific APIs, and framework-specific architecture unless they are needed to explain behavior.

## Before Starting

Confirm:
- Source chat history file path
- Target output directory (default: `shared/prompts/specs/`)
- Topic focus if the chat covers multiple independent topics

If the user does not provide all details, infer from the conversation and proceed.

## Process

1. **Read the entire conversation** from start to finish.
2. **Extract decisions by topic**: collect requirements, constraints, tolerances, edge cases, and examples.
3. **Resolve contradictions**: later statements override earlier ones. Drop ideas that were explicitly abandoned.
4. **Separate specification from implementation**: keep behavior and policy; remove code-level instructions and language-specific mechanics.
5. **Classify requirement strength**: identify what is mandatory, optional, and out of scope.
6. **Organize into one spec document** using clear headings and concise decision tables where helpful.
7. **Record gaps honestly**: if an important behavior is unresolved, list it under `Open Questions` instead of inventing a rule.

## Document Structure

Use a single markdown file with:
- `# {Title}` naming the shared specification clearly
- A short context line including the source conversation date
- `## Purpose`
- `## Scope`
- `## Terms` (only if needed)
- `## Requirements` grouped by behavior area
- `## Decision Tables` or `## Conformance Examples` for concrete expected outcomes
- `## Out of Scope`
- `## Open Questions`

## Existing Files

When the output directory already contains files:

- List filenames and directory structure to avoid naming collisions.
- Do not read the contents of existing files.
- Do not update or overwrite existing files.

## Output

Save as `{short-description}.md` in `shared/prompts/specs/` unless the user asks for a different location.

Derive the filename description from the specification title.

Filename rules:
- Use stable topic-based kebab-case names.
- Do not include dates or timestamps.
- Do not include source chat history filenames or path fragments.
- Avoid redundant suffix/prefix words like `shared`, `spec`, or `specification` when the directory already conveys that context.

Source-reference rules:
- Do not mention `secrets` repository paths or `secrets` directory structure in the generated shared spec.
- Do not mention the original chat history filename in the generated shared spec.
- If source provenance is needed, reference only high-level conversation context (for example, date and topic), unless the user explicitly requests exact paths/filenames.

Examples:
- `Retry and Timeout Policy` -> `retry-and-timeout-policy.md`
- `File Import Conflict Resolution` -> `file-import-conflict-resolution.md`

## Principles

- **Capture final decisions, not discussion.**
- **Stay language agnostic.** The output should be reusable across different coding AIs and languages.
- **Preserve explicit constraints.** If the user states a hard rule, keep it as a hard rule.
- **Be concrete.** Prefer clear expected outcomes over abstract advice.
- **Do not invent.** Unknowns belong in `Open Questions`.
