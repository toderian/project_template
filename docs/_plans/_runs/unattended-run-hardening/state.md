---
task: unattended-run-hardening
task_file: docs/specs/2026-11-26-unattended-run-hardening-plan.md
runtime: claude
mode: large
mode_reason: 8 phases; hook and subprocess surfaces
base_rev: da43501
branch: master
work_mode: default-branch
autonomy: L1
current_phase: 0
updated: 2026-11-26T00:00:00
---
# Run ledger — unattended-run-hardening

| Phase | Status | Attempt | Spec | Quality | Security | Open | Commit | Agent |
|---|---|---|---|---|---|---|---|---|
| 0 | reviewing | 2 | PASS | PASS | n/a | 0 | — | — |
| 1 | pending | 0 | — | — | — | 0 | — | — |
| 2 | pending | 0 | — | — | — | 0 | — | — |
| 3 | pending | 0 | — | — | — | 0 | — | — |
| 4 | pending | 0 | — | — | — | 0 | — | — |
| 5 | fixing | 3 | FAIL | FAIL | FAIL | 6 | — | — |
| 6 | pending | 0 | — | — | — | 0 | — | — |
| 7 | pending | 0 | — | — | — | 0 | — | — |

Phase 0: BASE 54e23a5
Phase 5: BASE 54e23a5 (lane B)
Note: plan without the task ledger; run directory written by hand per references/run-state.md
Note: order per the revised plan: phase 0; lane A = phases 1, 2, 3, 4 serial; lane B = phases 5, 6 in a worktree; merge B after phase 4; phase 7 last
Note: this session runs the installed plugin (1.14.0), whose hooks lack run-guard.sh; the guard is armed but no hook reads it here
Note: architecture review: plan-critic REVISE (6 blocking), peer codex REVISE (4); plan revised and reconciled, no rerun
Decision: watchdog budget per resume or total — total, divided by the resume cap — why: the smaller spend of the two readings of D3 — cost if wrong: a resume runs out of budget early and the owner raises it
Decision: may the watchdog resume a session recorded in bypassPermissions — no, unless arm was given --allow-bypass, recorded per task — why: an unattended restart in bypass mode is the largest risk the review named — cost if wrong: a night run in bypass mode is not restarted until the owner adds the flag
Decision: where the live suite runs — by hand per phase and before release, not in run-all.sh — why: pre-commit runs run-all.sh and the suite spends tokens — cost if wrong: a regression is seen at release instead of at commit
Decision: report filename date — commit date of base_rev, keeping D2's pattern — why: a rerun after midnight must name the same file — cost if wrong: the date shows the run's start, not the morning it is read
Note: lane B: worktree ../project_template-lane-b, branch lane-b/driver, phases 5 then 6; phase 5 started alongside phase 0 without its E7 scenario, which is added once the phase 0 harness is merged into the lane
Interface: Runner.runnable(state, pending) -> list[int]; phase_deps(task, n) -> list[int] in lib/task_run.py (phase 5, for phase 6)
Phase 5: fix round 1/3 (12 open: spec 0/2/2, quality 1/4/3, security 0/4/3, merged in phase-5/findings-1.md)
Phase 0: fix round 1/3 (9 open: spec 0/2/4, quality 1/5/4, merged in phase-0/findings-1.md); security n/a (test harness and a document, reviewed for session safety under quality)
Note: Phase 5 fix 1: code net +76 (plugins/agents-core/lib/task_run.py), now +185/-26 against a Shape of ~150
Phase 5: fix round 2/3 (round 1 closed 10 of 12; 6 open: 3 important, 3 minor, in phase-5/findings-2.md)
Phase 0: re-review PASS 0/0/3; minors A, B fixed by the orchestrator and E1 rerun green on the real CLI
Ruling: facts file wording (stream vs transcript, "fires at the interval" on one firing) — accepted as-is — cost if wrong: a reader overestimates the scheduler evidence; fact 5 is already "partly"
Interface: hooks.json has a SessionStart matcher for startup only; phase 1 adds resume and compact (facts 2)
Interface: the session process id is CLAUDE_PID in the Bash tool environment, not $PPID (fact 3); the Stop payload carries permission_mode (fact 8)
Interface: scheduler wakeups never fire under claude -p, and -p stays alive only while a background job runs (facts 5, 9): the watchdog's headless resume cannot rely on the heartbeat
Interface: live scenarios are scripts/tests/live/eN-<name>.sh sourcing live/lib.sh (fresh_repo, run_claude, stop_hook_codes, row_status, marker_inactive, fail); run with bash scripts/tests/test-unattended-live.sh EN
