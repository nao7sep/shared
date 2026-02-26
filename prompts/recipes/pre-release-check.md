# Pre-Release Check

Perform a full pre-release review of a specified app using the playbook and standard recipes.

## Before Starting

1. Read the playbook at `~/code/shared/PLAYBOOK.md` and internalize conventions, tooling, and engineering standards.
2. Identify the app: the user should specify the app name or directory. Locate it under `~/code/`. If ambiguous, ask before proceeding.

## Recipe Order

Run the following recipes in sequence. Complete each fully before moving to the next. If a recipe produces a plan file, note its path before continuing.

1. **Update Dependencies** — `~/code/shared/prompts/recipes/update-dependencies.md`
   Ensures the app ships with current, secure dependencies. Fix any test breakage before continuing.

2. **Review Code** — `~/code/shared/prompts/recipes/review-code.md`
   Catch bugs, logic errors, security issues, and architectural violations.

3. **Check Platform Compatibility** — `~/code/shared/prompts/recipes/check-platform-compat.md`
   Audit for cross-platform issues relevant to the app's target platforms.

4. **Review Docs** — `~/code/shared/prompts/recipes/review-docs.md`
   Verify documentation matches the current implementation.

5. **Refactor Code** *(optional)* — `~/code/shared/prompts/recipes/refactor-code.md`
   Run only if the user explicitly requests it or findings are clearly blocking. Pre-release is not the ideal time for structural changes.

## Output

After all recipes complete, produce a brief inline summary:
- App name and directory
- Status per recipe: pass / findings inline / plan file generated
- Any blockers that should be resolved before release
- Any non-blocking notes for the next iteration

Generate a summary file only if findings are non-trivial. If all recipes pass cleanly, report inline.
