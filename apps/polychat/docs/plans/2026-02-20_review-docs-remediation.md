# PolyChat Documentation Review Remediation Plan (2026-02-20)

## Scope Reviewed
- `README.md`
- CLI help output from `uv run polychat --help`
- REPL help text from `/help` (`src/polychat/commands/misc.py`)
- CLI usage/error text (`src/polychat/cli.py`)

## Findings

### 1. README states outdated default profile directories
- Severity: High
- Impact: New users are told generated profile defaults are `~/polychat/...`, but generated templates now use `~/.polychat/...`.
- Evidence:
  - `README.md:39` claims `~/polychat/...`.
  - `README.md:262` and `README.md:263` use `~/polychat/chats` and `~/polychat/logs`.
  - Actual defaults come from `src/polychat/constants.py:27`, `src/polychat/constants.py:33`, `src/polychat/constants.py:34`.
  - Template writer uses those defaults in `src/polychat/profile.py:268` and `src/polychat/profile.py:269`.

### 2. README omits `api_keys.type = "direct"` despite template using it
- Severity: Medium
- Impact: Users following API key docs may miss a supported config mode that appears in the generated profile (Grok default).
- Evidence:
  - README API key section only documents `env`, `keychain`, `json` (`README.md:316` onward).
  - Template includes `"type": "direct"` for Grok (`src/polychat/profile.py:285` to `src/polychat/profile.py:288`).

### 3. CLI `--chat` help says it prompts automatically when omitted, but runtime does not
- Severity: Medium
- Impact: CLI help sets incorrect expectation for startup behavior.
- Evidence:
  - Help text says: `"optional, will prompt if not provided"` in `src/polychat/cli.py:58`.
  - Runtime simply starts without a chat unless `-c` is provided (`src/polychat/cli.py:110` to `src/polychat/cli.py:115`), then REPL instructs user to use `/new` or `/open`.

## Remediation Plan

1. Update `README.md` to match current defaults and generated template behavior.
- Replace `~/polychat/...` references with `~/.polychat/...` where describing generated defaults.
- Align profile example `chats_dir`/`logs_dir` with actual generated template defaults.
- Keep path mapping examples as examples, but avoid implying they are generated defaults.

2. Expand API key documentation in `README.md`.
- Add a `direct` example:
```json
{
  "type": "direct",
  "value": "xai-..."
}
```
- Clarify when `direct` is useful and caution against committing plaintext secrets.

3. Correct CLI help copy for `-c/--chat`.
- Change help text in `src/polychat/cli.py` from:
  - `optional, will prompt if not provided`
- To:
  - `optional; start without a chat and use /new or /open`
- Regenerate/re-verify `polychat --help` output.

4. Add lightweight documentation drift checks.
- Add a doc validation test that asserts:
  - Profile template defaults for `chats_dir`/`logs_dir` are reflected in README.
  - API key types listed in docs include all supported template types (`env`, `keychain`, `json`, `direct`).
- This prevents future drift after profile/template changes.

## Verification Checklist
- Run: `uv run polychat --help`
- Run: `uv run polychat init -p /tmp/polychat-doc-check.json` and inspect generated JSON keys/paths.
- Confirm README sections now match both outputs and source constants.
