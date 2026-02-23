# Organize Conversation Into One Document

Convert AI conversation content into one well-organized reference document.

## Before Starting

Ask the user:
- What is the core topic? (drives title and filename description)
- Who will read this? (affects tone and assumed knowledge)
- Any specific sections to prioritize?
- Where should it be saved? (optional)

## Process

1. **Read the entire conversation** and identify key decisions, requirements, constraints, examples, and open questions.
2. **Resolve contradictions**: later statements override earlier ones. Drop ideas that were explicitly abandoned.
3. **Extract the final guidance**: keep what a reader needs to understand and apply the conversation outcome. Remove exploratory tangents.
4. **Organize into one document** using clear headings and logical flow.
5. **Do not invent missing details**: if something important is not stated in the conversation, record it under `Open Questions` instead of filling it in.

## Document Structure

Use a single markdown file with:
- `# {Title}` describing the topic clearly
- A short opening context for audience and purpose
- Major sections grouped by topic (use `##` and `###` as needed)
- Concrete examples and actionable guidance where possible
- `## Open Questions` for unresolved items

If topics build on each other, order sections by dependency. If topics are independent, use self-contained sections.

## Output

Save as `{YYYY-MM-DD}_{short-description}.md` in a location relevant to the current app/task context.

Derive the filename description from the document title (e.g., "API Transition Guide" becomes `2026-02-20_api-transition-guide.md`).

## Principles

- **Organize, do not expand.** Keep output grounded in the conversation rather than adding new material.
- **Capture decisions, not discussion.** The output should be usable without reading the original conversation.
- **Preserve intent.** Keep expressed preferences and constraints.
- **Be specific.** Favor concrete behavior and examples over vague advice.
- **Stay honest about gaps.** If something important is missing from the conversation, call it out in `Open Questions`.
