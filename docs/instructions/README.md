# Instructions Library

Reusable instruction files for common AI-assisted tasks.

## Purpose

This folder contains instruction files that can be referenced in AI conversations to execute common patterns efficiently.

## How to Use

### In AI Conversation

```
Please read ~/code/shared/instructions/split-conversation-into-docs.md
and apply it to this conversation.
```

AI will:
1. Read the instruction file
2. Follow the steps described
3. Ask for required input (if any)
4. Execute the task

### Benefits

- **Consistency**: Same process every time
- **Efficiency**: No need to re-explain the pattern
- **Refinement**: Improve the instruction file over time
- **Knowledge capture**: Your process becomes documentation

## Creating New Instructions

When you find yourself:
- Explaining the same process to AI multiple times
- Wanting to standardize how something is done
- Needing a complex multi-step task automated

**Create an instruction file following the template**:

```markdown
# [Action Title]

## Purpose
[One sentence]

## When to Use
[Bullet points]

## Prerequisites
[What must exist first]

## Input Required
[What AI needs to ask you]

## Steps
[Numbered, specific steps]

## Output
[What gets created]

## Example
[Concrete example]
```

## Available Instructions

- **split-conversation-into-docs.md**: Convert conversation content into ordered reference documents
- *(Add more as you create them)*

## Tips

- **Be specific**: "Generate TypeScript types from Pydantic models" not "Make types"
- **Include examples**: Show concrete input/output
- **Assume AI competence**: Don't explain basic concepts, just specify what to do
- **Test it**: Use the instruction in a real conversation, refine if needed
- **Version implicitly**: Update the file in place, git history tracks changes

## Naming Conventions

- Use kebab-case: `do-something-specific.md`
- Use verbs: `split-`, `generate-`, `setup-`, `create-`
- Be specific: `setup-fastapi-project.md` not `setup-project.md`
