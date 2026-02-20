# tk Documentation Review Plan (2026-02-20)

## Goal
Bring user-facing docs/help in sync with actual runtime behavior for `shared/apps/tk`.

## Evidence Reviewed
- `README.md`
- CLI help output: `uv run --directory shared/apps/tk tk --help`, `uv run --directory shared/apps/tk tk init --help`
- REPL help output: `printf 'help\nexit\n' | uv run --directory shared/apps/tk tk -p <profile>`
- Source of user-facing behavior:
  - `src/tk/cli.py`
  - `src/tk/repl.py`
  - `src/tk/dispatcher.py`
  - `src/tk/prompts.py`
  - `src/tk/commands.py`

## Non-Minor Findings

1. Multi-word `--note` examples in README do not work as documented.
- Docs claim: examples like `d 1 --note "deployed to prod" --date ...` and `c 2 --note "no longer needed"`.
- Actual behavior: REPL parser uses `line.split()` and only consumes one token after `--note`, so quoted multi-word notes break command parsing and produce usage errors.
- References:
  - `README.md:179`
  - `README.md:185`
  - `README.md:242`
  - `src/tk/repl.py:13`
  - `src/tk/repl.py:39`
  - `src/tk/dispatcher.py:92`
- Impact: users following docs hit command errors.
- Plan:
  - Decide product direction:
    - Option A: implement shell-style parsing (`shlex.split`) so quoted notes work.
    - Option B: keep parser as-is and rewrite docs to avoid quoted `--note` examples.
  - Preferred: Option A (aligns with existing README examples and user expectations).

2. README delete confirmation prompt text is inaccurate.
- Docs show: `Delete this task? (yes/no): yes`
- Actual prompt: `Delete permanently? (yes/N):`
- References:
  - `README.md:119`
  - `src/tk/prompts.py:75`
- Impact: low-level confusion and mismatched expectations.
- Plan:
  - Update README prompt transcript to match runtime prompt exactly.

3. Command descriptions for `today`/`yesterday` are inaccurate in both README and REPL help.
- Docs/help imply completed-only tasks.
- Actual behavior includes both `done` and `cancelled` tasks (all handled tasks).
- References:
  - `README.md:170`
  - `README.md:171`
  - `src/tk/dispatcher.py:178`
  - `src/tk/dispatcher.py:179`
  - `src/tk/commands.py:67`
  - `src/tk/commands.py:322`
  - `src/tk/commands.py:327`
- Impact: users may assume cancelled tasks are excluded.
- Plan:
  - Update README wording to "handled tasks".
  - Update REPL help text in dispatcher for `today`/`yesterday`.

4. REPL exposes `init <profile_path>` but it is undocumented and missing from REPL help.
- Runtime includes `init` in command registry and it works in REPL.
- README command list and REPL `help` output omit it.
- References:
  - `src/tk/dispatcher.py:59`
  - `src/tk/dispatcher.py:192`
  - `README.md:141`
  - `src/tk/dispatcher.py:167`
- Impact: undocumented user-visible feature and inconsistent command surface.
- Plan:
  - Decide product direction:
    - Option A: keep `init` in REPL and document it in README/help.
    - Option B: remove `init` from REPL registry and keep `init` as CLI subcommand only.
  - Preferred: Option B for cleaner mental model (profile lifecycle via CLI, task lifecycle via REPL).

5. Troubleshooting entry maps the wrong error to the wrong cause.
- Docs state "Unknown command" should be fixed by running `list` or `history`.
- Actual message for stale/missing list mapping is `Run 'list' or 'history' first`; unknown command is a different error path.
- References:
  - `README.md:265`
  - `src/tk/session.py:41`
  - `src/tk/dispatcher.py:222`
- Impact: sends users to wrong remediation path.
- Plan:
  - Rewrite troubleshooting item to separate:
    - "Run 'list' or 'history' first" errors (number mapping issue)
    - "Unknown command" errors (typo/unsupported command)

## Minor Findings

1. Duplicate debug-mode guidance appears in both Troubleshooting and Advanced Usage.
- References:
  - `README.md:271`
  - `README.md:278`
- Plan:
  - Keep one section and cross-link to avoid repetition.

2. README does not explicitly include license/support pointers.
- Standard expectation for user-facing README includes acknowledgment of license/support.
- Plan:
  - Add a short "License" section (`MIT`, link to `LICENSE`) and a short "Support" section (how to report issues for this repo).

## Execution Steps
1. Decide two product choices:
- parser behavior for quoted notes (Option A vs B)
- REPL `init` command surface (Option A vs B)
2. Update `README.md` command examples and troubleshooting text.
3. Update REPL help text in `src/tk/dispatcher.py` for `today`/`yesterday` (and `init` depending on choice).
4. If Option A for parsing is selected, update parser in `src/tk/repl.py` and add tests for quoted flags.
5. Run tests and help-output checks.

## Validation Checklist
- `uv run --directory shared/apps/tk tk --help`
- `uv run --directory shared/apps/tk tk init --help`
- `printf 'help\nexit\n' | uv run --directory shared/apps/tk tk -p <profile>`
- If parser updated: verify both commands work:
  - `d 1 --note "multi word" --date 2026-02-05`
  - `c 1 --note "multi word"`
- Confirm every README command example is runnable as written.
