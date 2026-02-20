# Plan From Conversation

Distill an AI conversation into a structured implementation plan for the app discussed.

## Process

1. **Read the entire conversation** and identify every decision, requirement, constraint, and open question discussed.
2. **Resolve contradictions**: later statements override earlier ones. If something was discussed but explicitly abandoned, drop it.
3. **Extract the final picture**: what the app does, who it's for, how it should work. Discard exploratory tangents that didn't lead to a conclusion.
4. **Organize into a plan** using the structure below.

## Plan Structure

The H1 title should identify the app. Use the app name if one was decided during the conversation. If no name was decided, use a concise description of what the app does (e.g., "CLI Bookmark Manager", "Markdown Link Checker"). Do not ask the user for a name — just pick the best title from what you know.

```markdown
# {Title}

Implementation plan generated from conversation on {YYYY-MM-DD}.

## Overview
What the app does in 2–3 sentences.

## Requirements
Concrete, actionable requirements distilled from the conversation.
Group by area (e.g., core behavior, CLI interface, configuration, output).

## Architecture
Key structural decisions: modules, data flow, external dependencies.
Only include what was discussed or clearly implied — do not invent architecture.

## Implementation Steps
Ordered list of steps to build the app from scratch.
Each step should be small enough to implement and verify independently.
Number them sequentially; note dependencies where one step must complete before another.

## Open Questions
Anything that was raised but not resolved in the conversation.
```

## Output Location

Save the plan as `{YYYY-MM-DD}_{short-kebab-description}.md` in the workspace root (the directory where the coding agent was initiated). If the project directory and `docs/plans/` already exist, save there instead.

Derive the filename description from the plan title (e.g., a plan titled "CLI Bookmark Manager" becomes `2026-02-20_cli-bookmark-manager.md`).

## Principles

- **Capture decisions, not discussion.** The plan is not a transcript summary — it's a blueprint. A reader who never saw the conversation should be able to build the app from this document alone.
- **Preserve intent.** If the user expressed a preference (e.g., "keep it simple", "no external services"), carry that forward as a constraint.
- **Be specific.** "Handle errors properly" is not a requirement. "Surface all errors to the user via stderr with a non-zero exit code" is.
- **Stay honest about gaps.** If the conversation didn't cover something important (e.g., persistence, authentication, deployment), call it out in Open Questions rather than inventing an answer.
