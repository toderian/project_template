# Final fix wave: findings merged from final-review-1, -2, -peer, -simplicity

Repo /home/vi/work/repos/project_template, branch master, HEAD bac94d4. Read AGENTS.md first.
Rules for both lanes: edit only the files of your lane; no commit, stage or stash; python3 stdlib
only; every fix gets a test that fails without it (say how you checked); run only your own test
files, not run-all.sh, no `claude`/`codex` sessions, no live suite; never touch
~/.local/state/agents-template/run-guard or a process you did not start. Reply in at most 15 lines:
per finding what you changed and the test name, then `## Status: DONE | DONE_WITH_CONCERNS | BLOCKED`.

## Lane W: plugins/agents-core/lib/run_watch.py, scripts/tests/test_run_watch.py

W1 [critical] A stale `kind=BLOCKED` in `<session>.status` switches the watchdog off silently
   (run_watch.py ~431-434). `.status` is written only at a stop the hook lets through, so after the
   owner answered and the session worked on, BLOCKED is still there; when the session then dies the
   watcher sees BLOCKED + dead, the notify is deduped, it exits 0. Fix: BLOCKED counts as current
   only when no guarded path (`scan()["paths"]`) changed after the status file's `last_stop`
   (fall back to the status file's mtime); a stale BLOCKED falls through to the normal dead / idle
   path. Test: BLOCKED status, then a target file touched later, dead pid: the session is restarted.
   A fresh BLOCKED keeps today's behaviour.
W2 [important] `Watcher.at` runs every helper in the marker's cwd (added in bac94d4). The marker is
   session-writable: a missing cwd makes every notify fail (`refused-cwd` never delivered), and
   `agents.notifyCommand` is read from that directory. Fix: the marker cwd is used for
   `at task report` only; `at notify` runs in the watcher's own cwd as before. Correct the comment.
   Tests: marker cwd missing: `refused-cwd` is delivered; marker cwd = another git repo with its
   own `agents.notifyCommand`: that command does not run.
W3 [critical] The watcher's report at "finished" overwrites the committed morning report with the
   poorer archived form: the run is finished only when the task left `_todos/`, and closeout has
   removed `_runs/<ID>/` by then. Fix: report only the ids whose `docs/tasks_manager/_runs/<ID>/state.md`
   exists under the marker cwd; no ids, no call (this also covers a state-only marker, which called
   `at task report` with no ids). Test in the real closeout shape (task archived, `_runs/<ID>`
   removed, a committed report present): the file is byte-identical afterwards and the tree clean.
   Keep test_the_report_is_written_in_the_runs_repository_wherever_the_watcher_started green.
W4 [important] `scan()`: a state-file target that is empty or has no table row counts as finished.
   Fix: a state file with zero rows makes `complete` False (unknown, never "finished"). Test: a
   truncated state.md does not produce "Run finished".
W5 [important] A failed `at task report` at "finished" is only logged, then the record is removed.
   Fix: send one more notification ("Morning report not written: run
   `at task report <ids>`"), not deduped through a hook key. Test: an unwritable or invalid
   `_reports` path gives that notification.
Size: run_watch.py may grow to at most 400 code lines (no blanks, comments, docstrings); do not
squeeze lines to get there.

## Lane D: plugins/agents-core/lib/task_run.py, task_lanes.py, task_report.py, scripts/tests/test_task_run.py, scripts/tests/test_task_report.py

D1 [important] `DONE` includes `reviewing` (task_run.py:39, used at ~904 and task_lanes.py:70), so
   an uncommitted row satisfies `After:`. Case: driver killed during phase 2's review, rerun with
   `--lanes 2`, phase 3 `After: 2` with a disjoint fence: both run in parallel. Fix: `reviewing`
   satisfies `After:` only under `--no-commit`. Test with that case (serial and lanes).
D2 [important] task_report.py:108 (and :32): in a run not marked unattended `park()` writes
   `Note: blocked phase N: ...` (task_run.py:586-589), which the report does not match. Fix: match
   `Note: (parked|blocked) phase N`; "Needs you" shows the reason and the kept worktree path.
D3 [important] A `RunError` before a phase starts (red baseline check, dirty tree) leaves no row
   change and no note, and the report says "Nothing open."; the same for rows a killed driver left
   `implementing`. Fix: (a) `run()` appends `Note: run aborted: <reason>` to state.md when it exits
   on a RunError (once per identical reason); (b) the report lists under "Needs you" every row of an
   unarchived task that is neither `committed` nor already listed, with its status, and the last
   `Note: run aborted` line. An archived task and a task with every row committed still say
   "Nothing open." Keep the report's rerun byte-identical.
D4 [minor] The report is an untracked file in `docs/tasks_manager/_reports/`, and the next
   `at task run` refuses the dirty tree (task_run.py:560-563). Fix: `dirty()` ignores
   `docs/tasks_manager/_reports/`, as it ignores the run directory. Test.
D5 [minor] task_lanes.py:267-269: the lane's `driver.log` starts as the committed copy and all of it
   is appended back, so entries multiply per wave. Fix: append only what the lane added. Test: one
   wave, the number of log entries equals the number of calls.
D6 [important] A ledger script that dies with a traceback passes: `post_phase_checks`
   (task_run.py:755-769) keeps only lines starting `ERROR`, and the sync calls (task_run.py:737,
   task_lanes.py:311) ignore the exit code. Fix: a nonzero exit with no `ERROR` line reports the
   last output line; a failed sync is treated like a failed check (the phase or wave does not
   continue silently). Test with a ledger script that exits 1 printing a traceback only.
D7 [minor, simplicity] task_lanes.py:254 copies `unattended` and `cap_continue` onto each lane
   Runner by hand (set in `_run`, task_run.py:925-926). Derive both in `Runner.__init__` from
   `self.task` and `args`; delete the copy.
