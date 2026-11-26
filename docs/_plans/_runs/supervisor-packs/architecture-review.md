Plan-critic (claude), round 1, 2026-11-26. Verdict: REVISE, composite 2.6. Saved in short form; the
plan revision answers each item.

Blocking:
- B1 Phase 1: skipping all of `.local/` at landing deletes worker-written local files (`git worktree remove` deletes ignored files, sup.py:263).
- B2 Phase 4: linked local paths skipped by name lose a file that replaced its link; link type and the "path exists" case unspecified.
- B3 Phase 4: discarding "ledger files" drops hand-written area page edits; `_active.md`/`_done.md` conflicts are already resolved (sup.py:174-181, test_sup_land.py:209).

Other:
- C1 guard tables (sup_guard.py:98,114) refuse `pack --branch` and `ready --pack`.
- C2 `_branch_exists` (sup_digest.py:130) keys `branches` by directory name beside the hub; slugs forbid `_`.
- C3 `task_lanes.PATH_RE` rejects `slug:path`.
- C4 `cmd_init` copies named profile keys only (sup_tick.py:243,259).
- C5 a blocked task is dropped silently; nothing tells the owner.
- C6 sibling commits land before the hub landing; a task that never lands leaves them.
- C7 a write outside the cwd under the worker's permission mode was never tried.
- C8 ceilings too low (Phase 1 about 250, Phase 2 about 60).
- C9 the plan extends an inheritance that reads a `Parent` row not in the task format.

## Status: DONE_WITH_CONCERNS
## Architecture verdict: REVISE
