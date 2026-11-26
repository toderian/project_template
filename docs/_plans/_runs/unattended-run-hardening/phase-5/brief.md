# Brief: unattended-run-hardening, Phase 5: The scripted driver learns the marks

Plan: /home/vi/work/repos/project_template/docs/specs/2026-11-26-unattended-run-hardening-plan.md.
Read "#### Phase 5", §"Shared design" (the "Shared files and lanes" paragraph) and E7 in
§"End-to-end tests". Implement only Phase 5.

## Phase checklist
- `at task run` reads `After:` lines (convention: plugins/agents-tasks/skills/task-ledger/references/todo-convention.md).
  A row that ends `blocked` or `parked` no longer ends the run: phases that do not depend on it
  still run; its dependants are set `parked` with a note.
- With `Execution: unattended`, a phase at the fix-loop cap follows the line
  `At review cap: park | continue` in the task's `### Unattended run` section (fixed key; missing
  means `park`). `continue` commits with a `Decision:` line naming the open findings and never
  applies to a critical finding.
- `at task run <ID> <ID>...` runs a chain in the given order, skipping a task whose `Blocked by`
  is not done.
- Exit code 0 only when every row is committed; 4 when it finished with parked rows.
- `scripts/tests/test_task_run.py` cases for each bullet.
- Shape: ≤ ~150 new code lines in `plugins/agents-core/lib/task_run.py`.

## Checks
- `python3 scripts/tests/test_task_run.py` (or however run-all.sh invokes it) passes.
- `bash scripts/tests/run-all.sh` green.

## Orchestrator notes
- You work in the LANE WORKTREE `/home/vi/work/repos/project_template-lane-b` (branch
  `lane-b/driver`). Edit and run everything there. The only file you write outside it is your
  report (path below). Do NOT commit, push or merge; the orchestrator commits.
- Work mode: lane branch, autonomy L1.
- Scope fence: `plugins/agents-core/lib/task_run.py`; `plugins/agents-core/lib/at.py` (ONLY the
  `task run` argument block and its dispatch, nothing in run-guard or elsewhere: another lane edits
  the rest of that file); `scripts/tests/test_task_run.py`;
  `plugins/agents-core/skills/execute-plan/references/run-state.md` (ONLY the "Scripted driver"
  section: document the new behaviour, flags and exit code 4). No other file. Do not edit
  `plugins/agents-core/skills/unattended-run/SKILL.md` (Phase 7 writes the `At review cap:` line there).
- The live scenario E7 is not part of this dispatch: its harness is being built in another lane.
- Existing statuses: `pending | implementing | reviewing | fixing | committed | blocked | parked`.
  Keep `--retry-blocked` and the lock behaviour working. State what happens to exit codes that
  existed before (list them in the report).
- Repo rules (AGENTS.md): python3 stdlib only; never hand-edit generated files; run
  `python3 scripts/build.py` if a source it reads changed.
- Interface for Phase 6 (parallel lanes, next in this lane): report the function that answers
  "which phases are runnable now" and how `After:` is parsed, as one `Interface:` line.

## Report contract
Write the full report to /home/vi/work/repos/project_template/docs/_plans/_runs/unattended-run-hardening/phase-5/report.md,
`## Test plan` first. Reply in at most 15 lines ending with:
## Status: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
