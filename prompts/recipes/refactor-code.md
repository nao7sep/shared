# Refactor Code

Identify high-ROI structural improvements in the current project's codebase.

## Scope

Read source code files only. Skip markdown (except README.md), plain text, logs, and data files.

## What To Look For

### Responsibility Splitting

- A module has a problem only when you can name two distinct responsibilities with independent reasons to change. File size and function length are never evidence of a problem by themselves.
- Recommend a split only when there is concrete evidence: mixed abstraction levels, tangled layers, or tests that require unrelated setup to exercise one behavior.
- For each split recommendation, name the two responsibilities and cite the evidence. If you cannot, do not recommend the split.
- Avoid "misc/utils dumping ground" refactors; each new file must have a clear, singular responsibility.
- Refactors must preserve behavior first: use small reversible moves and keep tests and API compatibility intact.

### Abstraction Opportunities

- No interfaces/protocols for a single implementation — that's premature.
- When two or more concrete implementations exist (or clearly will), extract a shared protocol.
- Three repeated code blocks are better than a bad abstraction, but five repeated blocks probably need one.

### Dead Code

- Unused imports, unreachable branches, commented-out code blocks, functions with no callers.
- Code guarded by conditions that can never be true given the current logic.

### Naming and Clarity

- Variables or functions whose names don't describe what they do.
- Boolean parameters that make call sites unreadable (consider replacing with named arguments or enums).
- Abbreviations that save typing but cost readability.

### Simplification

- Overly defensive code: checks for conditions that are guaranteed by the type system or earlier validation.
- Nested conditionals that can be flattened with early returns.
- Manual implementations of things the standard library already provides.

## What Not To Look For

- Bugs, security issues, or error handling problems — those belong in a review-code pass.
- Formatting or style enforcement.
- Performance optimizations unless the current code is clearly wasteful (e.g., O(n²) where O(n) is trivial).

## Output

- All good: report inline, no file.
- Minor improvements that can be applied quickly: report inline and suggest fixing them immediately.
- Non-minor findings: generate a plan as `{YYYY-MM-DD}_{short-description}.md` in a location relevant to the current app/task context, with specific file references, current state, proposed state, and rationale for each recommendation.
