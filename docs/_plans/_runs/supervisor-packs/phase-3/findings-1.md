# Phase 3, fix round 1: open findings

Required shape for 1 and 3 (one rule, no new state): `next_tasks` holds a task back only for a HEALTHY wait: it
has open blockers, every one of them is a task of the same pack, and the pack's edges are valid now (`_edges`
does not refuse). In every other case the task is offered as before, and `_refusal` (which the watcher's
`start-worker` call runs) refuses with the reason, so the existing `start_refused` event and its notice tell the
owner. `_refusal` therefore reports, in this order: an unreadable task file; an `_edges` refusal of the pack; an
open blocker.

1. [C] sup_workers.py:347-351, sup_digest.py:253-256 — an unreadable task file is a silent wait
   (review-quality.md #1). Per the shape: offered, refused by name through `_refusal`. `_waits` in the digest shows
   a fixed marker (for example `task file unreadable`) instead of nothing. Rewrite the test that pins "never offered".
2. [I] task_run.py:1186 — non-ASCII digits (review-quality.md #2). `blocker_ids` uses `[0-9]`; `_blockers` drops an
   id that `sup_state.TASK` does not match, so `st.landed` cannot raise there.
3. [I] sup_workers.py:347-354 — an edge that appears after `start-pack` stalls with no refusal
   (review-quality.md #3). Per the shape. Call `_edges` once per pack per pass, not per task.
4. [M] sup_workers.py:306-315 — check the cycle before the serial order, and name an edge that is on the cycle
   (follow blockers from a stuck task until a task repeats); a self-edge reads as a cycle
   (review-quality.md #4,#5, review-spec.md #1,#2).
5. [M] sup_workers.py:604 — in `cmd_start_pack` the pack state check comes before `_edges` (review-spec.md #3).
6. [M] tests — add: unreadable file in a serial pack is offered and `start-worker` refuses by name, status shows
   the marker; `RM-١` in a cell neither raises nor blocks; an outside blocker and a cycle written after
   `start-pack` are offered and refused with the edge named; the cycle message for a serial self-edge and for a
   task that only waits on a cycle.

Not in this round (ruled): the parse count per pass (review-quality.md #6).
