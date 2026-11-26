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
| 0 | pending | 0 | — | — | — | 0 | — | — |
| 1 | pending | 0 | — | — | — | 0 | — | — |
| 2 | pending | 0 | — | — | — | 0 | — | — |
| 3 | pending | 0 | — | — | — | 0 | — | — |
| 4 | pending | 0 | — | — | — | 0 | — | — |
| 5 | pending | 0 | — | — | — | 0 | — | — |
| 6 | pending | 0 | — | — | — | 0 | — | — |
| 7 | pending | 0 | — | — | — | 0 | — | — |

Note: plan without the task ledger; run directory written by hand per references/run-state.md
Note: order per the revised plan: phase 0; lane A = phases 1, 2, 3, 4 serial; lane B = phases 5, 6 in a worktree; merge B after phase 4; phase 7 last
Note: this session runs the installed plugin (1.14.0), whose hooks lack run-guard.sh; the guard is armed but no hook reads it here
Note: architecture review: plan-critic REVISE (6 blocking), peer codex REVISE (4); plan revised and reconciled, no rerun
Decision: watchdog budget per resume or total — total, divided by the resume cap — why: the smaller spend of the two readings of D3 — cost if wrong: a resume runs out of budget early and the owner raises it
Decision: may the watchdog resume a session recorded in bypassPermissions — no, unless arm was given --allow-bypass, recorded per task — why: an unattended restart in bypass mode is the largest risk the review named — cost if wrong: a night run in bypass mode is not restarted until the owner adds the flag
Decision: where the live suite runs — by hand per phase and before release, not in run-all.sh — why: pre-commit runs run-all.sh and the suite spends tokens — cost if wrong: a regression is seen at release instead of at commit
Decision: report filename date — commit date of base_rev, keeping D2's pattern — why: a rerun after midnight must name the same file — cost if wrong: the date shows the run's start, not the morning it is read
