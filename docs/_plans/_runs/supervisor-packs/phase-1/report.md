# Phase 1 report (saved by the orchestrator from the implementer's reply; its Write tool was refused)

## Test plan
| Behaviour | Layer | Test (scripts/tests) |
|---|---|---|
| `pack --branch` records `branches`; a rewrite without `--branch` keeps them; `start-pack` makes branch and worktree, safe twice, refuses a foreign path | unit | test_sup_workers: test_start_pack_makes_branch_and_worktree_and_is_safe_twice_and_refuses_a_foreign_path |
| attach to an existing branch; integration `N/A` falls back to the checked-out branch | unit | test_start_pack_attaches_to_an_existing_branch_and_falls_back_to_the_checked_out_one_for_na |
| unknown slug, slug without a map line, bad branch, default or integration branch, slug twice: refused by name | unit | test_pack_branch_refuses_an_unknown_slug_a_slug_without_a_map_line_and_a_bad_branch |
| `start-worker` writes a resolving map; `pack["tips"]` kept by a second `start-pack` and a failed worker start | unit | test_start_worker_writes_a_map_that_resolves_and_keeps_the_first_tip_in_the_pack |
| empty `branches`: no worktree, no map | unit | test_a_pack_without_branches_writes_no_map_and_no_worktree |
| two tasks on one repo never offered together; the second follows the first landing | unit | test_two_tasks_on_one_pack_repo_are_never_offered_together_and_the_second_follows_the_first_landing |
| hand `start-worker` refuses a held repo, a relative map path, a symlinked `.local` | unit | test_hand_start_refuses_a_task_whose_repo_is_held_and_a_relative_map_path_and_a_linked_map_dir |
| guard accepts a repeated `--branch slug=branch`, refuses metacharacters | unit | test_sup_guard: test_pack_branch_takes_slug_equals_branch_repeated_and_refuses_metacharacters |

## Round 0
sup_workers.py: `_repos`, `_checkout`, `_task_repos`, `_valid_branch`, `_git`, `_pack_worktrees`, `_write_map`;
`pack --branch`; `start-pack` (git first, then the lock); the `next_tasks` repo rule; two prompt sentences.
sup_guard.py: class `slug=branch`, `--branch` on `at sup pack`, `REPEATABLE`.

## Fix round 1
All 12 items of findings-1.md: `sibling_base` deleted, `pack["tips"]` written once by `start-pack`; integration
cell validated; default and integration branch refused; `_task_repos` on `task_brief.parse_task`; `_refusal`
knows the repo rule; `_git` refuses on OSError/timeout; duplicate slug, relative map path, symlinked `.local`
refused; `branches` compared under the lock; tests added. No test for items 7 and 11.

## Tests run (implementer)
test_sup_workers 28 OK, test_sup_guard 25 OK, test_sup_state 18 OK, test_sup_digest 16 OK, test_sup_flow 3 OK.

## Open
`next_tasks` and `_refusal` read `Repos` rows from the hub working tree: a task file only on a task branch is not seen.

## Status: DONE_WITH_CONCERNS (code net about 159 against the ceiling of 150)
