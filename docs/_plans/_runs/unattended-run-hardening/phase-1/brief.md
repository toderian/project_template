# Brief: unattended-run-hardening, Phase 1: Marker schema, and re-inject the run after a compaction or resume

Plan: docs/specs/2026-11-26-unattended-run-hardening-plan.md. Read §"Shared design" (the marker
files table and the Lifecycle paragraph are the contract), "#### Phase 1", and E2 in
§"End-to-end tests". Read docs/meta/2026-11-26-run-guard-facts.md (facts 2, 3, 7, 8). Implement only Phase 1.

## Phase checklist
- Marker schema and lifecycle of §"Shared design": `at run-guard arm` writes the `meta` lines
  (`pid` from CLAUDE_PID, `cwd`, `armed`); `run-guard.sh` writes `<session>.status`
  (`last_stop`, `kind` = WAITING | BLOCKED | GAVE_UP | EMPTY | DONE, `text`, `transcript`, `mode`)
  at every stop it lets through, including the five-sent-back and empty-message pass-throughs, and
  marks DONE instead of deleting the marker; a DONE marker is inactive (stops pass, no reminder);
  a new `arm` resets it; `status` and `disarm` and the 14-day prune know the new files
  (`.status`, `.count`, and the later `.sent/`, `.watch`).
- `hooks/run-guard-remind.sh`, a SessionStart hook for `compact` and `resume`: when this session's
  marker has open targets, print which tasks are open, the first open row, and "load
  `agents-core:execute-plan` and resume from `state.md`". Prints nothing otherwise; always exit 0.
- The open-target scan is one shared function in `plugins/agents-core/hooks/lib/`, used by this
  hook and `run-guard.sh` (no second copy).
- `hooks.json` entry (SessionStart matchers for resume and compact; today only startup exists);
  `python3 scripts/build.py`; hook tests: open run prints, no marker is silent, finished run is
  silent, missing `jq` is silent, a DONE marker lets a stop through, `.status` content per kind.
- Live scenario `scripts/tests/live/e2-compaction.sh` (E2): three-phase task, compaction forced
  after phase 1; passes when the reminder hook's text is in the transcript after the compaction and
  phases 2-3 are committed with no further prompt.
- Shape: ≤ ~90 new code lines (hooks + at.py, tests excluded); `run-guard.sh` gives the scan away.

## Checks
- `bash plugins/agents-core/hooks/tests/test-hooks.sh`, `bash scripts/tests/test-at.sh`
- `bash scripts/tests/run-all.sh` green (it checks generated files and hook counts:
  scripts/tests/test-codex-live.sh and scripts/tests/test_codex_compat.py assert hook counts; update them)
- `bash scripts/tests/test-unattended-live.sh E1 E2` on the real CLI

## Orchestrator notes
- Work mode default-branch (master), autonomy L1. Do NOT commit, push or release.
- Scope fence: `plugins/agents-core/hooks/` (run-guard.sh, run-guard-remind.sh, lib/, hooks.json,
  generated hooks.codex.json, tests/test-hooks.sh), `plugins/agents-core/lib/at.py` (ONLY
  `run_guard_dir`, `cmd_run_guard` and its parser block), `scripts/tests/test-at.sh`,
  `scripts/tests/test-codex-live.sh` and `scripts/tests/test_codex_compat.py` (count assertions
  only), `scripts/tests/live/e2-compaction.sh`, `scripts/tests/live/lib.sh` (only if E2 needs a
  helper; keep `marker_inactive` true for a DONE status),
  `plugins/agents-core/skills/execute-plan/references/run-state.md` (ONLY the "Run guard" section),
  `README.md` (hook count only). Do not touch `lib/task_run.py` or the "Scripted driver" section:
  another lane edits them.
- Interface: hooks.json has a SessionStart matcher for startup only; add resume and compact (fact 2).
- Interface: the session process id is CLAUDE_PID in the Bash tool environment, not $PPID (fact 3);
  the Stop payload carries permission_mode (fact 8).
- Interface: live scenarios are scripts/tests/live/eN-<name>.sh sourcing live/lib.sh (fresh_repo,
  run_claude, stop_hook_codes, row_status, marker_inactive, fail).
- Later phases build on this: Phase 2 adds notifications keyed on `kind` with dedupe files
  `<session>.sent/<event>`; Phase 4 adds a watchdog reading `meta` and `.status` and writing
  `<session>.watch`. Do not implement them, but do not make them awkward: keep `.status` writing in
  one function, written atomically (temp file + mv).
- Never trap a session: every hook path that cannot decide lets the stop through; the remind hook
  always exits 0. `text` in `.status` is one line, length-capped, never executed or eval'd.
- Live runs: cheapest model, budget cap per session, whole phase ≤ 5 USD, scratch repos and the
  harness's private AGENTS_RUN_GUARD_DIR only. How to force a compaction headless is in the facts
  file (fact 7).
- Repo rules: bash, python3 stdlib, jq only; generated files only via build.py.

## Report contract
Write the full report to docs/_plans/_runs/unattended-run-hardening/phase-1/report.md if your
tools allow it (else put it in the reply), `## Test plan` first. Reply in at most 20 lines with the
last lines of the E1 E2 run, ending with:
## Status: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
