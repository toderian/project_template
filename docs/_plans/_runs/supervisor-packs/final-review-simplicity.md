Stage: simplicity, final review.

## Status: DONE_WITH_CONCERNS
## Verdict: FAIL (two duplicate rules that can drift; no item saves 10 lines; safe-now total about 8 lines)
## Findings: 9 (C:0 I:2 M:7)
Safe now:
1. [I] sup_workers.py:794-797 — `_write_map` rebuilds the pack worktree path that `_pack_wt` owns. Use `_pack_wt`.
2. [I] slug rule in three places: sup_workers.py:71 `SLUG`, task_lanes.py:37 in `ENTRY_RE`, sup_guard.py:64. `task_lanes` owns `SLUG`, `ENTRY_RE` built from it, sup_workers imports it; the guard copy stays with a pointer comment.
3. [M] sup.py:408 — unused import `sup_state as st` in `pack_problems`.
4. [M] sup_state.py:182,191 — `profile_local(check=True)`: both callers pass False. Drop the parameter.
5. [M] sup_digest.py:196-201 — `_pack_ready_lines` tests `slug in tips` three times.
6. [M] sup_workers.py:641-642 — `cmd_close_pack` calls `_clean(wt)` twice.
7. [M] test_sup_land.py:307,:414 — registry header inline twice.
Later:
8. [M] sup_digest.py:129-132 — `_branch_exists` could be `w._tip`; decide first whether the legacy key `"."` is supported.
9. [M] "landed or archived" rule at sup.py:427 and sup_workers.py:295, while `_edges`, `_held`, `next_tasks` use `_landed` only: a task archived without a landed event is skipped by `ready --pack` but counted open by `_edges`. Needs one rule.
