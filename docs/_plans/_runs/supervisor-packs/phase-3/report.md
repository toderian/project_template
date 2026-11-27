# Phase 3 report (saved by the orchestrator from the implementer's reply)

## Test plan
| Behaviour | Layer | Test |
|---|---|---|
| parallel pack: blocked task offered only after its blocker landed; a started or done-unlanded blocker does not free it; hand start-worker refused naming the blocker; cell "`RM-1` Phase 1, RM-1" parses | next_tasks + cmd_start_worker | test_sup_workers: test_blocked_by_offers_the_task_after_its_blocker_landed_and_a_started_blocker_alone_does_not_free_it |
| archived blocker outside the pack does not block; `—`/`none` name no blocker | next_tasks | test_an_archived_blocker_outside_the_pack_does_not_block_and_dash_or_none_names_no_blocker |
| three refusals (open blocker outside the pack; serial order against an edge; cycle and self-blocker); start-pack re-checks | cmd_pack / cmd_start_pack | test_pack_and_start_pack_refuse_an_open_blocker_outside_the_pack_a_serial_order_against_an_edge_and_a_cycle |
| unreadable task file refused by name, never offered | next_tasks + _refusal | test_an_unreadable_task_file_is_refused_by_name_and_never_offered |
| `waits for <ID>` in status and prompt digest; gone after landing | digest | test_sup_digest: test_a_task_with_an_open_blocker_shows_waits_for_and_a_landed_blocker_does_not |
| open_blockers unchanged | existing | test_task_run.py unmodified |

## Changed
task_run.py: `blocker_ids(cell)`; `open_blockers` built on it. sup_workers.py: `_task_meta`, `_blockers` (the one
rule), `_edges` (three refusals), used by `next_tasks`, `_refusal`, `cmd_pack`, `cmd_start_pack`. sup_digest.py: `_waits`.

## Tests (implementer): workers 33 OK, digest 18 OK, task_run 63 OK
## Open: the cycle refusal may name an edge of a task that only waits on a cycle, not one on it.
## Status: DONE_WITH_CONCERNS (66 net physical lines against 60)

## Fix round 1 (from the implementer's reply)
1,3 `next_tasks` calls `_edges` once per pack and holds a task back only for a healthy wait; `_refusal` reports
unreadable file, `_edges` refusal, open blocker; `_waits` shows ` task file unreadable`. 2 `[0-9]` and ids filtered by
`st.TASK`. 4 order: outside blocker, cycle (edge on the cycle), serial order. 5 state check before `_edges` in
start-pack. 6 four tests added, one rewritten. Extra: `_edges` calls `_landed` only for a task with open blockers.
Tests: workers 36 OK, digest 18 OK, watch 35 OK, flow 4 OK, task_run 63 OK. Code net 81 against 60.

## Fix round 2 (from the implementer's reply)
1 `_starts` keeps a backoff for every refusal; `BACKOFF[0] = 300`: a refusal before `claude` ran is retried every
5 minutes; event still once per (task, reason). 2 tasks of a pack `_edges` refuses go after the healthy packs'
tasks. 3 `_edges` returns `{task: [open blockers]}`; flag and second try removed. 4 landed test before the file
read; test_start_worker_registers_the_row... keeps git on its PATH. 5 two tests added.
Tests: workers 37 OK, digest 18 OK, watch 36 OK, flow 4 OK. Code net 78 against 60.
