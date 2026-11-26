# Brief: unattended-run-hardening, Phase 3: Morning report (live E4)

Plan: /home/vi/work/repos/project_template/docs/specs/2026-11-26-unattended-run-hardening-plan.md.
Read "#### Phase 3" and row E4 with the harness description in "End-to-end tests". Implement Phase 3.

## Phase checklist
- `at task report <TASK-ID>... [--since <rev>]` writes `docs/tasks_manager/_reports/<date>-<TASK-ID>.md`
  (`<date>` is the commit date of the run's `base_rev`, so a rerun on another day names the same
  file), committed with the run; `at ledger check` (agents-tasks, `sync_todo_ledgers.py`) accepts
  the directory. Content: per task its status, each phase row with its commit, verdicts and open
  count; every `Decision:`, `Ruling:` and `Note: parked:` line; for tasks already archived, the same
  lines from their completion summary; the commits since `--since`; and "needs you" first: parked
  questions.
- `agents-tasks:complete-task` copies `Note: parked:` lines into the completion summary next to
  `Ruling:` and `Decision:`, so closeout loses none of them.
- Deterministic: built only from task files, run states and `git log`, so it can be run by the
  agent, by the watchdog, or by the owner, and a rerun gives the same file (byte-identical).
- `agents-core:unattended-run` step 6 runs it before closeout instead of composing the summary by
  hand, and puts the parked questions through `agents-core:ask`.
- Unit tests on a fixture with one committed, one parked and one archived task.
- Shape: one new module in `plugins/agents-core/lib/`, ≤ ~200 code lines.
- Live scenario `scripts/tests/live/e4-report.sh` (E4): its own run with one parked row and one
  `Decision:`, then `at task report`; passes when the file lists the commits, the parked question
  under "needs you" and the `Decision:` line, and a second run of the command leaves it byte-identical.

## Checks
- the new unit test file, `bash scripts/tests/test-at.sh`, `python3 scripts/build.py`,
  `bash scripts/tests/run-all.sh`: green.
- `bash scripts/tests/test-unattended-live.sh E4` on the real CLI.

## Orchestrator notes
- You work ONLY in the worktree `/home/vi/work/repos/project_template-lane-c` (branch
  `lane-c/report`, HEAD 721558a, clean). Do NOT commit, stage, stash, push or merge.
- Two other agents work in other checkouts at the same time; your work is merged with theirs
  later, so keep shared files to small, self-contained regions. Scope fence:
  new module `plugins/agents-core/lib/task_report.py`; `plugins/agents-core/lib/at.py` ONLY the
  `task` subcommand dispatch/usage for `report` (do not touch the run-guard block, `cmd_notify`
  area near it, or `task run`); new `scripts/tests/test_task_report.py` (and its registration in
  `scripts/tests/run-all.sh` if tests are listed there, one line); `scripts/tests/live/e4-report.sh`;
  `plugins/agents-tasks/skills/complete-task/SKILL.md` (the summary step only);
  `plugins/agents-core/skills/unattended-run/SKILL.md` (step 6 ONLY: another agent edits the step 2
  table); the ledger checker `sync_todo_ledgers.py` under plugins/agents-tasks if `_reports/` must
  be accepted; `plugins/agents-core/skills/execute-plan/references/run-state.md` only a new short
  section at the END of the file; README.md only one line in the command list. Do NOT edit
  `plugins/agents-core/hooks/`, `lib/task_run.py`, `scripts/tests/test_task_run.py`,
  `scripts/tests/live/lib.sh`, `scripts/tests/test-at.sh` (put CLI tests in your own test file).
- Interface: run state format and `Decision:` / `Ruling:` / `Note:` lines are described in
  `plugins/agents-core/skills/execute-plan/references/run-state.md`; state.md frontmatter has
  `base_rev`; the scripted driver writes `Note: parked phase N: ...` lines; orchestrating skills write
  `Note: parked: <question>`. Decide which of these count as "parked questions" from the docs and
  say so in the report; reuse the parser in lib/task_run.py (`State`) by import if it fits, do not
  copy it and do not edit it.
- Interface: live scenarios are `scripts/tests/live/eN-<name>.sh` sourcing `live/lib.sh` (make_repo,
  write_state, run_claude, row_status, fail, new_uuid); run with
  `bash scripts/tests/test-unattended-live.sh E4`. Assertions read files, never model prose.
  Test helpers use here-strings, not `printf | grep -q` (SIGPIPE under pipefail).
- Security surface: task ids are validated (`[A-Z][A-Z0-9]*-<n>`) before they reach a path;
  `--since` and `base_rev` go to git as argv after validation (hex or a ref that `git rev-parse
  --verify` accepts, never a leading dash); the report repeats `Decision:`/`Ruling:`/`Note:` lines
  verbatim but never file contents; it writes only under `docs/tasks_manager/_reports/`.
- Determinism: no wall-clock time, no absolute paths, stable ordering, `git log` with a fixed
  format; a task with no run state and no archive is an error naming it (exit 2), not an empty file.
- Decision: the report filename date is the commit date of `base_rev`.
- Live runs: cheapest model, harness budget caps, whole phase ≤ 4 USD, scratch repos only, private
  AGENTS_RUN_GUARD_DIR; never touch ~/.local/state/agents-template/run-guard.
- Repo rules (AGENTS.md): python3 stdlib only; generated files only via `python3 scripts/build.py`;
  skill text names skills by full `plugin:skill` id; SKILL.md ≤ 500 lines.
- If a tool refuses a write or a command, say so; do not work around a refusal. Leave no temp
  directories in the worktree.

## Report contract
Your chat reply is the report, at most 30 lines: `## Test plan` first, design in four lines (what
counts as parked, where archived tasks' lines come from, how the date and ordering are fixed, what
`--since` defaults to), files changed, check results with the last lines of the live run, code
lines of the new module, and end with:
## Status: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
