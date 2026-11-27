# Phase 4, lane A (code): implementer's reply, condensed. Lane B: report-lane-b.md

## Test plan
ready pack / 1.17.0 pack; one line per task problem; slugs of Repos row and Files; phase in Blocked by, outside
blocker, cycle; resource the profile lacks; shared Files entry between tasks that can run together (not flagged:
serial, shared pack repo, edge direct or transitive, other repo); no hub, relative map path, missing pack, bad usage:
all in test_sup_land.py class PackReady, plus Ready.test_a_files_entry_with_a_slug_needs_the_slug_in_the_repos_row;
fence in test_task_run.py; guard rows in test_sup_guard.py.

## What changed
- task_lanes.py: ENTRY_RE, entry_ok(); fence accepts `slug:path`, returns entries unchanged; overlap compares strings.
- sup.py: _brief, _slugs, _resources; readiness refuses a Files slug missing from the Repos row; task_lines(tid, hub);
  pack_problems(profile, pack, hub) builds the lines and never raises; `ready --pack`.
- sup_workers.py: cmd_start_pack calls sup.pack_problems and refuses with the lines.
- sup_guard.py: rule `at sup ready --pack <name> [--profile]`.
- test_sup_workers.py setUp patches sup.task_lines to (None, [], []) because its packs have no task files; pack-level
  edge rules stay real there.

## Decisions
`src/` and `src/a.py` count as shared; landed tasks are skipped; lines ordered task readiness and resources, then
edge, phase, repo slug, shared file; an unreadable file gives one line; a Repos slug is a problem only when the map
gives it a path other than the hub and it has no pack branch; missing profile.json means no known resources;
`start-pack` newly refuses an unready pack (intended).

## Tests
guard 25 OK, land 45 OK, workers 37 OK, watch 37 OK, flow 4 OK, digest 18 OK, task_run -k fence 4 OK, -k lanes 3 OK.

## Open
Code net 107 against 80. No end-to-end test that start-pack refuses on a readiness line (test_sup_flow outside fence).

## Status: DONE_WITH_CONCERNS

## Fix round 1 (both lanes, from the replies)
Lane A: items 1-13 done. `pack_problems` catches ValueError; registry slug needs a pack branch with or without a map
line; `Repos` cell read only by `sw._task_repos(root, task, meta=None)`; `sup._slugs` and `task_lines` removed;
`readiness(task_parsed, path, known=None)`; one `task_brief` import (`sup._brief`); `task_lanes.split_entry`;
shared-file rule skipped when `_edges` refuses; corrupt profile.json is its own line; archived task skipped; phase
test `<ID>\W*phase\s*<digit>`; headings cleaned and cut to 60; `.` segment refused. test_sup_workers: setUp patch
removed, `write_task` helper, test that start-pack refuses on a readiness line.
Tests: workers 39 OK, guard 25 OK, land 46 OK, watch 37 OK, flow 4 OK, digest 18 OK, task_run -k fence 4, -k lanes 3 OK.
Lane B: items 14-18 done. README counts 21+28+19+8 = 76; prepare-pack 86 lines; build ok, compat 9 OK.
