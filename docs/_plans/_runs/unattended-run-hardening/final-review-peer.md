Peer: codex (model gpt-6-sol, effort default, cyber daybreak_blue), role reviewer, 2026-11-26T13:44:26

## Status: DONE_WITH_CONCERNS
## Verdict: FAIL
## Findings: 3 (C:3 I:0 M:0)

1. [C] `plugins/agents-core/lib/run_watch.py:195` — Empty or truncated `state.md` has zero parsed rows, so watcher can announce completion while work remains. Treat unreadable or rowless state as unknown; test interrupted writes.
2. [C] `plugins/agents-core/lib/run_watch.py:426` — If report write fails after a dead session finishes, watcher logs failure, deletes its record, and exits. Morning report may never exist. Preserve failure for retry or notify owner.
3. [C] `plugins/agents-core/lib/task_lanes.py:311` — Wave ignores ledger sync exit; `Runner.post_phase_checks` also ignores nonzero exits without `ERROR` text. A Python traceback can leave inconsistent ledgers in a committed wave. Check exit codes.

## Evidence

- Spec: Phase 0–7 code, live evidence, docs, and recorded decisions checked against plan. E9, E6 heartbeat, and release remain owner gated as brief states.
- Tests: `test_run_watch.py` 31, `test_task_report.py` 21, `test_task_run.py` 59, and `build.py --check` passed. Named `test-run-guard.sh` does not exist; hook tests live in `plugins/agents-core/hooks/tests/test-hooks.sh`. Existing tests miss three cases above.
- Size and commits: Flagged code growth has reasons in phase size reports and run state; no fixture or test ratio flag. First-parent phase commits match described scope.
- Consequence 1: Checked `at.py` report/watch routing, hook calls, `Runner.phase`, and wave calls; failures reach new watcher and lane paths.
- Consequence 2: `scan()` treats zero rows as complete; `post_phase_checks()` collects only output lines starting `ERROR`.
- Consequence 3: Watcher writes notifications, report, record and log; lanes write merges, task rows and ledgers. Three findings identify lost completion or ledger evidence.
- Consequence 4: Hook’s open-row scan and watchdog’s `scan()` can both mistake a rowless state for completion.
- Consequence 5: Report failure reaches watch log, then record is removed; ledger sync traceback can be ignored after commit.
- Consequence 6: Missing regression inputs are truncated `state.md`, unwritable `_reports`, and ledger script exiting nonzero with traceback only.
