Task description: Review this implementation plan before execution.
Acceptance criteria:
- The plan fits the existing architecture and local patterns.
- Phase boundaries are independently committable and do not hide cross-phase dependencies.
- Test strategy is sufficient for the stated acceptance criteria.
- Resolved specs are classified as planned intent vs implemented evidence before code edits.
- Risks, migrations, rollout concerns, and compatibility constraints are identified.
Scope fence: read-only; do not edit files. Do not run the test suite.
Context files: docs/specs/2026-11-26-supervisor-packs-plan.md (the plan),
docs/specs/2026-11-26-supervisor-session-plan.md (the built design, decisions D1-D25),
plugins/agents-core/lib/sup.py, sup_workers.py, sup_watch.py, sup_digest.py, sup_state.py,
plugins/agents-core/lib/task_run.py (open_blockers), plugins/agents-tasks/skills/supervise/SKILL.md,
plugins/agents-tasks/skills/task-ledger/references/todo-convention.md, scripts/tests/test_sup_*.py.
Check in particular: (1) do the functions and fields the plan names exist as it says (next_tasks,
pack `branches`, kept_ignored, done_check, readiness, how the hub's .local/repos.map and
.config/repos.project.md are read today); (2) are the line ceilings believable; (3) what breaks for a
1.17.0 profile and pack already on disk; (4) anything in Phase 4's ledger handling or linked local
paths that can lose a user's data.
Model hint: strongest available, highest effort.
Your reply is the review; at most 40 lines ending in:
## Status: DONE | DONE_WITH_CONCERNS | BLOCKED
## Architecture verdict: PROCEED | REVISE | BLOCKED
## Blocking findings: <count>, one line each
## Required plan changes: <one line each>
