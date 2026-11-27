# Phase 2 report (saved by the orchestrator from the implementer's reply)

## Test plan
| Behaviour | Layer | Test |
|---|---|---|
| dirty pack worktree refuses `land`, changes nothing | CLI, scratch repos | test_sup_land PackLand.test_a_dirty_pack_worktree_refuses_and_changes_nothing |
| hub commit body carries `<slug> <branch> <old>..<new>`; tip moves; only `.local/repos.map` skipped by kept_ignored | CLI | PackLand.test_the_hub_commit_carries_the_range_and_the_tip_moves |
| crash between hub commit and tips update: rerun converges, no second commit | CLI | PackLand.test_a_rerun_after_a_crash_between_the_commit_and_the_tips_moves_the_tips |
| `done` refuses above-tip branch or dirty worktree; names branch, count, "ready for PR"; `status` names repo, task, count | digest + CLI | test_sup_digest test_pack_repos_need_the_tip_and_a_clean_worktree_then_done_names_the_branch |
| 1.17.0 `branches` keyed by directory name | existing | test_pack_branches_must_exist |
| `close-pack` removes only a clean worktree at the tip, keeps the branch | command, real git | test_sup_workers test_close_pack_removes_only_a_clean_worktree_at_the_tip_and_keeps_the_branch |
| two tasks in order on one sibling repo, end to end | flow, fake claude | test_sup_flow test_a_pack_with_a_sibling_repo_runs_two_tasks_in_order_and_done_names_the_branch |

## Changed
sup_workers.py: `_pack_wt`, `_clean`, `_tip`, `land_ranges`, `advance_tips`, `pack_ahead`; `_task_repos` also reads
`_todos_archived`; `close-pack` removes clean pack worktrees at the tip, never `--force`, never a branch.
sup.py: `kept_ignored` skips `.local/repos.map`; `squash_and_commit(body)`; `cmd_land` calls `land_ranges`, then
advances tips after the hub commit. sup_digest.py: `_branch_exists` through the map; `_pack_repo_problems` in
`done_check`; `done` lines per repo; digest section COMMITS ABOVE THE LANDED TIP.

## Crash window
Order: squash commit, archive ref, `advance_tips`, branch delete. A crash before `advance_tips` leaves the hub
commit with the range and the old tip; `status` shows the repo above the tip, `done` refuses; the rerun sees the
`Archive:` line, skips the squash and advances the tips.

## Open (implementer)
- a task with no sibling repo in its `Repos` row that still commits there gets no range; only `done`/`status` catch it.
- `close-pack` "clean" = empty `git status --porcelain`: ignored files in a pack worktree are deleted by `git worktree remove`.
- `status` shows the repo while its worker runs (commits above the tip), naming the task.

## Tests (implementer): land 35 OK, digest 17 OK, workers 29 OK, flow 4 OK
## Status: DONE

## Fix round 1 (from the implementer's reply)
1 `pack_for_land(main, profile, task)`: land refuses when a pack with branches holds the task and the given
profile is not the holder. 2 `close-pack` keeps a worktree with ignored files (count from `sup.kept_ignored`).
3 `advance_tips(profile, pack, main, message)` reads the ranges from the hub landing commit; a tip moves only
forward. 4 `Refused` caught in `_pack_repo_problems`, `_pack_ready_lines`, `_ahead_lines`. 5 ready lines only for
repos with a tip. 6 integration cell through `_valid_branch`, refs as `refs/heads/`. 7 `close-pack` decides, then
writes `closed`, then removes. 8 tests added and PackLand shrunk. 9 comment on old == new.
Tests: land 36 OK, digest 17 OK, workers 29 OK, flow 4 OK. Code net 165 against the ceiling of 120.
