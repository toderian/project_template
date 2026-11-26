# Phase 0, open findings for fix round 1

Sources: review-spec.md and review-quality.md in this directory (line numbers and reproductions).

Harness safety and correctness (scripts/tests/live/lib.sh, test-unattended-live.sh):
1. [C] A session can never start outside the scratch directory: `set -euo pipefail`, every
   `REPO=$(...)` failure ends the scenario, and `run_claude` refuses a repo that is not under
   `${SCRATCH}/` with its own `.git`. A failed `mktemp` ends the run. (quality 1, 2)
2. [I] Ctrl-C or TERM stops the running session and the suite (exit 130), and a session that
   ignores TERM is killed. `need timeout`. (quality 3, 8)
3. [I] `stop_hook_codes` counts only the Stop hook whose command is the working tree's
   `run-guard.sh`. (quality 5, spec 6)
4. [I] A failing scenario prints the scratch repo, the stream file and the session transcript path
   (`transcript_of`). (quality 6)
5. [I] Flakiness: the runner retries a scenario a bounded number of times (default 2 attempts,
   each keeps its own scratch dir) and says so in its output; a pass after a retry is reported as
   such. (quality 4)

Scenario E1 (scripts/tests/live/e1-guard-holds.sh):
6. [I] Negative 1 is "same repo, another session armed and open, this session never armed": it
   must fail if the guard ignored the session id. (spec 1)

Facts file (docs/meta/2026-11-26-run-guard-facts.md):
7. [I] Fact 4: show a plugin hook (the working tree's run-guard.sh) ran in a session resumed with
   `--resume -p` and quote it, or mark that half "not observed". (spec 2)
8. [M] Mark as not observed what was not: the bypass-mode refusal (it came from the outer session,
   not the CLI), a completed scheduled turn under pty (it fired once, then stalled on a permission
   prompt), "same session_id" on resume unless quoted. (spec 3, 4, 5)
9. [M] No personal home path, real session ids or pids in the committed file: `~/.claude/projects/...`,
   `<session-id>`. Fix the `stop_hook_events` comment. (quality 7, 10)

Not required: removing transcripts of passing runs (quality 9) — note it in the harness header.
