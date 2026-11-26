reviewer (spec + quality), phase 7 text. Verdict: FAIL, findings 0/3/6. Checked against code; no suites run.
1. [important] run-state.md recovery: "fix, then reset" is the wrong order: `reset --hard` discards the fix (task_lanes.py:303-322, 108-118).
2. [important] run-state.md recovery: rows are `reviewing`, not parked, after the failure; a hand-merged lane is released only when its row is `committed` in state.md (task_lanes.py:139-140); the driver's note says "set the row to pending" (:149).
3. [important] unattended-run/SKILL.md: `at task run <ID> --harness codex` runs every open row on Codex and skips a parked row; needs `--phase N ... --retry-blocked` (task_run.py:955-957, 1067).
4. [minor] `--retry-blocked` is needed only once a rerun parked the row, and re-runs every blocked or parked row.
5. [minor] README, CHANGELOG: `--idle` and `--until` are not recorded caps (run_watch.py:52).
6. [minor] SKILL.md: nothing reads the four new lines; say they count as `Defaults` in step 5.
7. [minor] `--at-review-cap continue` works only in an unattended task and with no critical finding (task_run.py:926, 683).
8. [minor] CHANGELOG "Watchdog and heartbeat" says nothing about the heartbeat.
9. [minor] CHANGELOG: "once per event" holds only with `--event KEY --session ID`; the hook notifies for any guarded run.
## Status: DONE
## Verdict: FAIL
## Findings: 0/3/6
