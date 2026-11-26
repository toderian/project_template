## Status: DONE_WITH_CONCERNS
## Verdict: FAIL
## Findings: 6 (C:1 I:3 M:2)
1. [C] lib/run_watch.py:431-434 — a stale `kind=BLOCKED` switches the watchdog off silently. `.status` is rewritten only at a stop the hook lets through. Case: run goes BLOCKED, owner answers, session works on and dies mid-turn: the watcher sees BLOCKED + dead, the notify is deduped, it exits 0: no restart, no message. While the session lives the same branch skips the idle check. Reproduced. Fix: treat BLOCKED as current only if nothing changed after `last_stop`; otherwise fall through to the dead/idle path, or send a non-deduped "blocked and dead" event before exiting.
2. [I] run_watch.py:417 with :393-394 — every `at notify` of the watcher runs in the marker's cwd, which the session writes. (a) Missing cwd: `refused-cwd`, `gave-up` and `finished` fail with `[Errno 2]` and reach only the log. (b) `agents.notifyCommand` is read from the marker's cwd: another repository's command ran. The Stop hook avoids this (run-guard.sh:74). Fix: `cwd=self.cwd` only for `task report`.
3. [I] lib/task_run.py:39,904 (and task_lanes.py:70) — `DONE` includes `reviewing`, so an uncommitted row satisfies `After:`. Case: driver killed during phase 2's review, rerun with `--lanes 2`, phase 3 `After: 2` with a disjoint fence: both ran in parallel and were committed. Fix: count `reviewing` as done only under `--no-commit`.
4. [I] task_run.py:594-597,862-868 with task_report.py:104-120 — a `RunError` before a phase starts leaves no row change and no note; the report says "Nothing open." Same headline for rows left `implementing` by a killed driver. Fix: note the abort in state.md in `run()`; list every non-committed row of an unarchived task under "Needs you".
5. [M] task_report.py:164-167 vs task_run.py:560-563 — the report is an untracked file in `docs/tasks_manager/_reports/`; the next `at task run` refuses the dirty tree. Fix: exempt `_reports/` in `dirty()` or commit it with the bookkeeping.
6. [M] lib/task_lanes.py:267-269 — the lane's `driver.log` starts as the committed copy and all of it is appended back: 13 calls, 21 entries. Fix: append only what the lane added.
## Evidence
- test_run_watch.py and test_task_report.py green; test_task_run.py still running at hand-off.
- Experiments in scratch repos with their own AGENTS_RUN_GUARD_DIR; no repository file edited.
- Sound: hook and watcher produce the same event key; `.sent` exclusive create dedupes; `claude` gets argv, never a shell; wave undo keeps pre-existing untracked files.
- Missing test inputs: BLOCKED status older than the session's death; a marker cwd that does not exist; a `reviewing` row with `--lanes`; a red baseline check followed by `at task report`.
- Also: an `OSError` while `authorise` reads a task file is retried every tick with no notification (run_watch.py:298,502).
