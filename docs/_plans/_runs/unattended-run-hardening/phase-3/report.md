Phase 3 report (implementer reply, saved by the orchestrator).
## Test plan
scripts/tests/test_task_report.py (real git repo + `at` CLI): committed, parked and archived task each reported, "needs you" first, date from base_rev (archived without state: first commit of the task file), rerun byte-identical even after the report is committed; errors (bad id, unknown task, `--since -x`, unknown rev) exit 2 with no _reports/ dir. Live: scripts/tests/live/e4-report.sh.
## Design
Parked = every `Note: parked...` line (skill form `Note: parked: Q`, driver form `Note: parked phase N: ...`) plus every row `parked` or `blocked`; Decision:/Ruling:/Note: parked lines copied verbatim. Archived tasks: the same lines from the task file's `## Completion summary` only; neither state nor archive exits 2. Date = `git show -s --format=%cs <base_rev>`; ordering `git log --reverse --no-merges`, fixed format, commits touching only _reports/ excluded. `--since` defaults to base_rev; revs through `rev-parse --verify --end-of-options`; output only under docs/tasks_manager/_reports/; a symlinked _reports is refused. Reuses `State` from task_run by import.
## Checks
test_task_report 2 OK; build ok; test-at 348/0; run-all ok; live E4 PASS.
## Concerns
sync_todo_ledgers.py needed no change; E4's parked row and Decision: are fixture, the session only does the phase-1 commit; a report committed together with other work adds that commit to a later rerun's list.
## Status: DONE
