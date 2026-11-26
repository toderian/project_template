# Brief: unattended-run-hardening, Phase 6: Parallel lanes in the scripted driver (plus live E7, E8)

Plan: /home/vi/work/repos/project_template/docs/specs/2026-11-26-unattended-run-hardening-plan.md.
Read "#### Phase 6", "#### Phase 5" (already implemented, commit 52e97e9), and rows E7 and E8 with
the harness description in §"End-to-end tests". Implement Phase 6 and the two live scenarios.

## Phase checklist
- `at task run --lanes N` (default 1, at most 3): phases whose `After:` lines are satisfied and
  whose scope fences do not overlap run at the same time, each in its own worktree and lane
  branch, one process tree per lane. A phase without a stated scope fence never shares a wave.
  (Find how a phase states its scope fence in plugins/agents-tasks/skills/task-ledger/references/todo-convention.md
  and plugins/agents-core/skills/execute-parallel/SKILL.md; if no convention exists, use a
  `Files:` line under the phase heading and say so in the report, without editing those two files.)
- Bookkeeping stays in the integration checkout; the driver holds one lock for it (the existing
  run lock), so two lanes never write `state.md` at once.
- Integration per wave, lowest phase first: `git merge --no-ff`; the `--check` commands after each
  merge; a conflict or a red check parks that lane (worktree kept, noted in state.md) and the rest
  go on. The driver never resolves a conflict: a conflicted merge is aborted (`git merge --abort`).
- One `Stage: both` review of the wave's integrated diff before the next wave.
- Merged lanes are removed (`git worktree remove`, `git branch -d`); a killed driver leaves
  worktrees that the next run finds from the `Note: lane ...` lines and reuses or reports.
- Tests with the fake harness in scripts/tests/test_task_run.py: two independent phases run
  concurrently and merge; overlapping fences fall back to serial; a conflict parks one lane and
  commits the other; rerun after a kill.
- Shape: wave planning, worktrees and merging in their own module (plugins/agents-core/lib/, new
  file), ≤ ~350 code lines; a lane runs the existing phase loop through its own `Runner` on the
  lane worktree, no copy of that loop.
- Live scenarios (real CLI): `scripts/tests/live/e7-driver-marks.sh` (E7: `at task run` on a
  three-phase task where phase 2 cannot pass its check and phase 3 says `After: 1`; passes when
  phase 3 is committed, phase 2 and nothing else is `parked`, exit code 4) and
  `scripts/tests/live/e8-driver-lanes.sh` (E8: `--lanes 2` with two independent phases, both commits
  on the integration branch and no lane worktree left; then a variant where both edit the same
  line: one lane parked, the other committed, tree clean).

## Checks
- `python3 scripts/tests/test_task_run.py`; `bash scripts/tests/run-all.sh` green.
- `bash scripts/tests/test-unattended-live.sh E7 E8` on the real CLI.

## Orchestrator notes
- You work ONLY in the LANE WORKTREE `/home/vi/work/repos/project_template-lane-b` (branch
  `lane-b/driver`, clean, HEAD e46cb2c). Do NOT commit, push or merge; the orchestrator commits.
- Scope fence: `plugins/agents-core/lib/task_run.py`, the new lanes module in
  `plugins/agents-core/lib/`, `plugins/agents-core/lib/at.py` (ONLY the `task run` usage/argument
  block), `scripts/tests/test_task_run.py`, the fake harness under scripts/tests if it must learn
  concurrency, `plugins/agents-core/skills/execute-plan/references/run-state.md` (ONLY the
  "Scripted driver" section), `scripts/tests/live/e7-driver-marks.sh`,
  `scripts/tests/live/e8-driver-lanes.sh`. Do NOT edit `scripts/tests/live/lib.sh`,
  `test-unattended-live.sh`, anything under `plugins/agents-core/hooks/`, the run-guard block of
  at.py, or any SKILL.md: another lane is editing them. A helper a scenario needs lives in that
  scenario file.
- Interface: at task run exit codes: 0 all committed, 1 blocked or aborted, 2 bad arguments, id or
  After: graph, 4 finished with parked rows or a skipped chain task; flag --at-review-cap park|continue.
- Interface: Runner.must_not_have_committed(n, base), Runner.set_aside(state, n),
  Runner.runnable(state, pending), phase_deps(task, n), after_problems(task) in lib/task_run.py.
- Interface: live scenarios are scripts/tests/live/eN-<name>.sh sourcing live/lib.sh (fresh_repo,
  run_claude, stop_hook_codes, row_status, marker_inactive, fail); E7 and E8 call `at task run`
  with the real `claude` harness instead of `run_claude`, so they need their own budget and
  timeout flags (`--budget-usd`, `--timeout`, cheapest `--model`).
- Lessons from Phase 5's reviews, apply them from the start: nothing the driver decides may be
  read from a file an implementer can write; `set_aside` and commits use explicit pathspecs and
  never touch the user's staged work; a lane implementer that commits in its lane worktree must be
  handled deliberately (in a lane the phase commit is the driver's: decide and test what an
  implementer commit there means); every failure path leaves state.md saying where the work is
  (worktree path, branch); a rerun after a kill never deletes a worktree with uncommitted work.
- Security surface: subprocess and git arguments are argv lists, lane branch and worktree names
  derive only from validated task ids and phase numbers; worktrees are created beside the
  repository or under a directory you state, never inside a path taken from task content.
- Live runs: cheapest model, budget cap per dispatch, whole phase ≤ 10 USD, scratch repos only,
  the harness's private AGENTS_RUN_GUARD_DIR. Never touch ~/.local/state/agents-template/run-guard.
- Repo rules (AGENTS.md): python3 stdlib only; generated files only via `python3 scripts/build.py`.
- If a tool refuses a write or a command, say so in the report; do not work around a refusal.
  Leave no temp directories in the worktree (a `.codex-live.*` directory was left behind before).

## Report contract
Your chat reply is the report (you cannot write outside the worktree), at most 30 lines:
`## Test plan` first, design in five lines (how a wave is planned, where worktrees live, what the
lock covers, what a lane implementer commit means, what rerun-after-kill does), files changed,
check results with the last lines of the E7 E8 run, the numstat of the new module and task_run.py,
and end with:
## Status: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
