# Expand Conversation Into Docs Directory

Convert AI conversation content into a directory of documents that works as a standalone guide.

## Before Starting

Ask the user:
- What is the core topic? (becomes the folder name)
- Who will read this? (affects tone and assumed knowledge)
- Where should it be saved? (optional)
- Any specific splitting preferences?
- Any preferred documentation style (tutorial, reference, playbook, etc.)?

## Process

1. **Read the entire conversation** and identify key decisions, requirements, constraints, examples, and open questions.
2. **Resolve contradictions**: later statements override earlier ones. Drop ideas that were explicitly abandoned.
3. **Build from the final decisions**: use the conversation as the source of truth, then expand into docs that are useful without the original chat.
4. **Fill missing parts** needed for a standalone guide (setup context, terminology, expected workflows, caveats).
5. **Mark assumptions clearly**: when you infer missing details, state them in `README.md` and in the relevant document.

## Structure Decision

Analyze the content, identify major topics, then choose a structure:

- **Topics build on each other**: use numbered files (`01-`, `02-`, …) ordered by dependency. Each document can assume the previous ones were read.
- **Topics are independent**: use unnumbered files. Each document should be self-contained.

## Naming

- Folder name: kebab-case, specific enough to signal the topic (`transition-guide`, `api-patterns`) but not over-specific (`windows-to-mac-csharp-to-python-2026`).
- Don't repeat the folder name in document titles.

## Contents

Always include a `README.md` that explains:
- What the folder contains
- Reading order (if applicable)
- Context about the intended audience
- Key assumptions introduced while filling missing parts

Keep documents action-oriented and example-heavy. Ensure a new reader can understand and use the subject without seeing the original conversation.
