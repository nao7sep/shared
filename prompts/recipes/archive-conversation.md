# Archive Conversation

Convert AI conversation content into a well-organized folder of reference documents.

## Before Starting

Ask the user:
- What is the core topic? (becomes the folder name)
- Who will read this? (affects tone and assumed knowledge)
- Where should it be saved?
- Any specific splitting preferences?

## Structure Decision

Analyze the content, identify major topics, then choose a structure:

- **Topics build on each other**: use numbered files (`01-`, `02-`, …) ordered by dependency. Each document can assume the previous ones were read.
- **Topics are independent**: use unnumbered files. Each document should be self-contained.

Aim for 3–5 documents. Fewer than 3 probably doesn't need splitting. More than 10 suggests sub-folders or a narrower scope.

## Naming

- Folder name: kebab-case, specific enough to signal the topic (`transition-guide`, `api-patterns`) but not over-specific (`windows-to-mac-csharp-to-python-2026`).
- Don't repeat the folder name in document titles.

## Contents

Always include a `README.md` that explains:
- What the folder contains
- Reading order (if applicable)
- Context about the intended audience

Keep documents action-oriented and example-heavy. Avoid repeating context across documents — the folder name and README carry the shared context.
