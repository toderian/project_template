Re-review round 1, phase 1 (quality reviewer; covers the spec and security items of findings-1.md).
1-12: resolved (finding 1 reproduced again against `pack["tips"]`: tips unchanged after a failed restart and a second `start-pack`; 7 and 11 by reading/probe only, no test).

## Status: DONE
## Verdict: PASS
## Findings: 2 (C:0 I:0 M:2)
1. [M] plugins/agents-core/lib/sup_workers.py:519-525 — the repo rule lives twice (`next_tasks` and `_refusal`); one helper would serve both.
2. [M] plugins/agents-core/lib/sup_workers.py:128 — `sup.tasks_root()` raises `sup.Refuse`, not caught: traceback when agents-tasks is missing.
The 9 lines over the ceiling are justified by findings 2, 3 and 6-11.
Both fixed by the orchestrator after this reply: `_held` / `_pack_repos` shared by both callers; `_task_repos` turns `sup.Refuse` into `Refused`.
