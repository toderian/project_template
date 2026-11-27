## Status: DONE_WITH_CONCERNS
## Verdict: FAIL
## Findings: 6 (C:1 I:2 M:3)
1. [C] plugins/agents-core/lib/sup_workers.py:347-351 + sup_digest.py:253-256 — an unreadable task file in a running pack is a silent wait: never offered, so no `start_refused`; `_waits` swallows the `Refused`; a serial pack stalls whole.
2. [I] plugins/agents-core/lib/task_run.py:1186 — `\d+` matches non-ASCII digits; `sup_state.TASK` wants `[0-9]+`: a cell `RM-١` makes `st.landed` raise `ValueError` in `_blockers`; `next_tasks` and `digest()` die for the whole profile.
3. [I] plugins/agents-core/lib/sup_workers.py:347-354 — an edge that appears after `start-pack` (task file edited: outside blocker, or a cycle) stalls for ever with no refusal; status text equals a healthy wait.
4. [M] plugins/agents-core/lib/sup_workers.py:308-309 — the serial check runs before the cycle check and uses `>=`: a self-edge or a serial 2-cycle says "reorder the tasks".
5. [M] plugins/agents-core/lib/sup_workers.py:314-315 — the cycle refusal names the first stuck task, not a cycle edge.
6. [M] plugins/agents-core/lib/sup_workers.py:340-359 — the parallel loop parses every unstarted task file each pass (20 parses, 20-39 git calls, 0.08-0.19 s for 20 tasks).
