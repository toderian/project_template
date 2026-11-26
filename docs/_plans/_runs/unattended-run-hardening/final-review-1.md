## Status: DONE_WITH_CONCERNS
## Verdict: FAIL
## Findings: 6 (C:1 I:3 M:2)
1. [C] lib/run_watch.py:426 (with task_report.py:90-141) — the watchdog's "finished" report overwrites the committed morning report with a poorer one: a task target closes only when the task leaves `_todos/`, closeout removes `_runs/<ID>/`, so the watcher builds the archived form (no phase table, "None recorded.") and leaves the tree dirty. Reproduced. Fix: skip the report when the task has no run state; test in the real closeout shape.
2. [I] run_watch.py:383-394,417 — the phase 7 seam fix runs `at notify` in the marker's cwd: a missing cwd makes every notify raise (`refused-cwd` unsent), and the session-writable marker chooses the notify command, against the Decision at state.md:71. Fix: marker cwd for `task report` only.
3. [I] lib/task_report.py:108 (and :32) against task_run.py:586-589 — in a run not marked unattended `park()` writes `Note: blocked phase N: ...`, which the report never matches; "Needs you" drops the reason and the kept worktree path. Fix: match `Note: (parked|blocked) phase N`.
4. [I] hooks/run-guard.sh:137-149 with run_watch.py:431-434 — a send-back never updates `.status`, so `kind=BLOCKED` stays after the owner answers; a later death gives no restart and no message. Fix: BLOCKED is current only when no target changed after `last_stop`, or the hook clears the kind on a send-back.
5. [M] commit bac94d4 is typed `docs:` but carries a behaviour change in run_watch.py; fix in a separate `fix:` commit.
6. [M] run_watch.py:426 — a state-only marker finishes with `at task report` and no ids (exit 2, logged). Fix: skip when there are no ids.
## Evidence
- Findings 1-3 reproduced in scratch repos; finding 4 probed (BLOCKED + dead pid: exit 0, no `claude` call).
- build.py --check ok; test_run_watch 31 OK, test_task_report 21 OK, test_task_run OK.
- Size flags justified by state.md:61,114,118,134. No fixture or test-ratio flag.
- Other seams sound: hook and watcher event keys match; chain `Blocked by` lookup reads the archive; `Watch:` regex accepts the indented template.
- test_run_watch.py:138 cannot fail for finding 1: its fixture keeps `_runs/TST-001/state.md` after archiving.
