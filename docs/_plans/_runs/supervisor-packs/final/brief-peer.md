# Final whole-task review: supervisor packs

Repository: the current directory (a plugin marketplace; supervisor CLI `at sup`, python3 stdlib only, code in
plugins/agents-core/lib/sup*.py and task_lanes.py; tests are unittest files in scripts/tests/, each run as its own
process).
Plan: docs/specs/2026-11-26-supervisor-packs-plan.md (five phases, sections "Acceptance" and "Out of scope").
Diff: `git diff 3a36951 HEAD -- plugins scripts README.md` (also in docs/_plans/_runs/supervisor-packs/final/diff.patch).
Run state with rulings and interfaces: docs/_plans/_runs/supervisor-packs/state.md.

Review the whole change, read-only. Find defects a phase-by-phase review misses:
1. Interactions between phases: pack worktrees and tips (1, 2), `Blocked by` scheduling and the watcher's retry
   rule (3), pack readiness (4), `local` links and the landing guard (5).
2. Data loss and state corruption: `at sup land`, `close-pack`, `start-pack` restarts, a crash between two steps.
   The landing guard in `cmd_land` (sup.py, the loop above `touched = `) must stop every branch shape that makes the
   squash-merge delete or replace content the hub holds untracked or ignored.
3. Behaviour of a 1.17.0 profile and pack (no branches, no `local`, no `Blocked by`) is unchanged, except that
   `start-pack` now refuses an unready pack.
4. Each acceptance criterion of the plan that code can meet is met.
5. Documentation (plugins/agents-tasks/skills/supervise/SKILL.md, prepare-pack/SKILL.md, the todo convention) states
   only what the code does.
Do not report style, and do not report what state.md already rules, unless the ruling is wrong.

Reply: `## Verdict: PASS|FAIL`, then numbered findings `[C|I|M] file:line — defect — how to trigger`, most severe
first, at most 60 lines.
