# Brief: unattended-run-hardening, Phase 0: Spike the harness facts

Plan: docs/specs/2026-11-26-unattended-run-hardening-plan.md. Read §"Facts to confirm first",
§"Shared design", "#### Phase 0" and §"End-to-end tests" (harness description and row E1 with its
negative checks). Implement only Phase 0.

## Phase checklist
- A throwaway script and real Claude Code sessions answer facts 1-9; each answer is one line
  (yes / no / partly) with its evidence (payload dump, command, exit code) in
  `docs/meta/2026-11-26-run-guard-facts.md`.
- Each "no" names the phase it changes and how. A "no" on fact 9 says whether E6 can run in an
  interactive session driven through a pty (`script`, python `pty`) or must be manual.
- The harness `scripts/tests/test-unattended-live.sh [E1 ...]` and `scripts/tests/live/e1-guard-holds.sh`
  (scenario E1 plus its three negative checks), passing against the real CLI.

## Checks
- `bash scripts/tests/test-unattended-live.sh E1` exits 0 (real CLI; paste its last lines in the report).
- the facts file has nine answered lines.
- `bash scripts/tests/run-all.sh` stays green.

## Orchestrator notes
- Work mode default-branch (master), autonomy L1: local edits and checks only. Do NOT commit, push
  or release; the orchestrator commits.
- Scope fence: `docs/meta/2026-11-26-run-guard-facts.md`, `scripts/tests/test-unattended-live.sh`,
  `scripts/tests/live/`. Nothing else. Do not add the suite to `run-all.sh`, pre-commit or CI.
  Probe scripts and payload dumps live in a temp directory, not in the repo; quote the decisive
  lines in the facts file.
- Existing code to exercise: `plugins/agents-core/hooks/run-guard.sh`, `hooks/hooks.json`,
  `plugins/agents-core/bin/at run-guard arm|status|disarm` (lib/at.py `cmd_run_guard`).
- The installed plugin on this machine is an older release without run-guard. Load the plugins
  from this working tree (find the CLI flag in `claude --help`, e.g. a plugin directory flag) and
  confirm in the transcript that the working-tree Stop hook ran.
- Every probe and scenario session: cheapest model, `--max-budget-usd` (keep each ≤ 1 USD, whole
  phase ≤ 10 USD), a timeout, its own `AGENTS_RUN_GUARD_DIR` and a scratch git repo. Never arm or
  touch a marker under `~/.local/state/agents-template/run-guard`. Never resume or signal any
  session you did not start. A missing CLI is a failure, not a skip.
- Assertions read files (commits, state.md rows, marker, transcript hook entries), never model prose.
- A fact you cannot observe headless (for example fact 5, the scheduler) is answered "not observed"
  with what you tried; do not guess from documentation alone, but you may cite documentation as
  secondary evidence.
- Repo rules: bash, python3 stdlib and jq only. Prose in normal sentences.

## Report contract
Write the full report to docs/_plans/_runs/unattended-run-hardening/phase-0/report.md, `## Test plan`
first, then what you did, the nine answers in short, files changed, and anything later phases must
know. Reply in at most 15 lines ending with:
## Status: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
