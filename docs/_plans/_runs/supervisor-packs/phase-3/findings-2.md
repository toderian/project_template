# Phase 3, fix round 2: open findings

1. [C] sup_watch.py:285-289 — a start refused for a cause outside the task's own file is never retried when the
   cause goes away (re-review-1-quality.md #1). Decision of the orchestrator: a refusal that did not come from
   `claude` costs nothing to repeat (no session starts), so `_starts` retries it every 5 minutes without limit;
   the `claude` backoff (5 minutes, 15 minutes, then only on a change) stays as it is. The `start_refused` event is
   still sent once per (task, reason) through `_once`. sup_watch.py and scripts/tests/test_sup_watch.py are added
   to the scope fence for this finding only. Update the docstring of `_starts`.
2. [I] sup_workers.py:347-372 — tasks of an unhealthy pack (one `_edges` refuses) take the free slots before
   startable tasks of other packs (re-review-1-quality.md #2). Put them after the tasks of healthy packs before
   the slice by `free`.
3. [M] sup_workers.py:347-361,:692-698 — `_edges` returns the open blockers per task (`{task: [blockers]}`);
   `next_tasks` and `_refusal` read that instead of a `healthy` flag, a second `try` and a second parse
   (re-review-1-quality.md #3). This must give lines back.
4. [M] sup_workers.py:303 — test `not _landed(t)` before reading the task file, so a landed task's file is never
   read (re-review-1-quality.md #4).
5. [M] tests — add: a refused start is tried again after 5 minutes and starts when the blocker has landed (watch
   test, age the memory as the existing backoff test does); with cap 1, a healthy pack listed after an unhealthy
   one still starts its task.
