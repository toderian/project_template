reviewer, re-review of the final fix wave. Verdict: PASS, findings 0/0/5. All 12 items closed; guards mutation-checked; no false "report was not written" on a normal finished run.
1. [minor] lib/run_watch.py:420: the report is skipped silently when the marker cwd is a subdirectory of the repository, or absent. Fix: build the path from the marker's task root.
2. [minor] lib/task_run.py:884: the abort-note dedupe keeps a repeated reason at its old position, so the report's "last" note can be wrong. Fix: remove and re-append.
3. [minor] lib/task_lanes.py:310: a ledger-sync failure after a passed wave review leaves the wave open (recoverable and documented, but heavy). Fix: route it through undo + park.
4. [minor] task_run.py:931 and task_report.py:110: two guards have no failing test (the `set_aside` report exclude; `blocked` in the note regex).
5. [minor] run_watch.py:327: a session-written past `last_stop` makes a fresh BLOCKED stale, so a dead session is restarted within caps.
## Status: DONE
## Verdict: PASS
## Findings: 0/0/5
