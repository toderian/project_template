Re-review round 1, phase 3 (quality, spec items included).
1: resolved. 2: resolved. 3: open (the refusal arrives, the watcher never retries after the cause is gone). 4: resolved. 5: resolved. 6: resolved.

## Status: DONE_WITH_CONCERNS
## Verdict: FAIL
## Findings: 4 (C:1 I:1 M:2)
1. [C] plugins/agents-core/lib/sup_workers.py:347-360 with sup_watch.py:285-289 — a task refused for a cause outside its own file is never retried once the cause is gone: the `tried` key is owner touches + pack JSON + the task's own file hash. Probed: outside blocker lands, or a sibling file is repaired; the pack stalls until an owner touch.
2. [I] plugins/agents-core/lib/sup_workers.py:347-351,:372 — an unhealthy pack offers every task and they fill the free slots every pass: with cap 1 a healthy pack listed after it never starts.
3. [M] plugins/agents-core/lib/sup_workers.py:347-361,:692-698 — `healthy` flag plus a second `try` and a `_blockers` + `_edges` pair: have `_edges` return the deps and read them.
4. [M] plugins/agents-core/lib/sup_workers.py:303 — `_blockers` runs before `not _landed(t)`: an unreadable archived file of a landed task refuses the whole pack.
