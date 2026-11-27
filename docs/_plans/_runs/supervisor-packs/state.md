---
task: supervisor-packs
task_file: docs/specs/2026-11-26-supervisor-packs-plan.md
runtime: claude
mode: large
mode_reason: 5 phases; security surface (subprocess, git, file paths); public CLI contract
base_rev: 3a36951
branch: master
work_mode: default-branch
autonomy: L1
current_phase: 4
updated: 2026-11-26T14:00:00
---
# Run ledger — supervisor-packs

| Phase | Status | Attempt | Spec | Quality | Security | Open | Commit | Agent |
|---|---|---|---|---|---|---|---|---|
| 1 | committed | 2 | PASS | PASS | PASS | 0 | fc0c526 | — |
| 2 | committed | 3 | PASS | PASS | PASS | 0 | 37d7474 | — |
| 3 | committed | 4 | PASS | PASS | n/a | 0 | 5e6e330 | — |
| 4 | committed | 3 | PASS | PASS | PASS | 0 | PENDING | — |
| 5 | pending | 0 | — | — | — | 0 | — | — |

Note: owner gave full autonomy on 2026-11-26 ("no need to ask me", "full access"); push of master and a release were approved earlier for 1.17.0 only, so pushes and releases of this run are left to the owner
Note: architecture review round 1: plan-critic REVISE (3 blocking), peer BLOCKED (6); all confirmed and taken into the plan: only .local/repos.map skipped at landing, links checked at landing, no ledger discard, guard + task_lanes + sup_tick in scope, branches keyed by slug with 1.17.0 fallback, no silent Blocked-by wait, landed_tip checks, Phase 1 split in two, no new Parent inheritance, D21 unchanged
Phase 1: BASE 3a36951
Decision: does a worker on task/<ID> trip execute-plan's default-branch rule — not trialled; the worker prompt says the task branch is on purpose — why: cheaper and certain, no seed change — cost if wrong: a worker asks one question the supervisor answers
Note: fact (b) confirmed with a real headless session: write and commit in a sibling worktree outside cwd under --permission-mode auto, no denial
Ruling: REPEATABLE is global in sup_guard — accepted as-is, only --branch is in it and DEFAULT_MAIN is the only table with that flag — cost if wrong: an owner table with its own --branch flag accepts a repeat
Note: Phase 1 fix 1: code net +26 (sup_workers.py)
Phase 1: complete; fix round 1/3 (12 addressed), re-review PASS, 2 minor fixed by the orchestrator
Interface: sup_workers._repos(hub) -> ({slug: (default, integration)}, {slug: absolute path}); Refused on a relative map path  (phase 1)
Interface: sup_workers._checkout(hub, slug, mp) -> Path; pack worktree = <checkout>.parent/<checkout.name>-<pack name>  (phase 1)
Interface: sup_workers._task_repos(root, task) -> set of slugs; _pack_repos(pack, hub, task); _held(profile, pack, hub, rows) -> {slug: task}  (phase 1)
Interface: sup_workers._pack_worktrees(profile, pack) -> {slug: tip}, idempotent; _git(path, *args) raises Refused on OSError/timeout; _valid_branch(b)  (phase 1)
Interface: pack["branches"] {slug: branch}; pack["tips"] {slug: sha} written once by start-pack, phase 2 advances it at landing (this is the plan's `landed_tip`)  (phase 1)
Note: open from phase 1: Repos rows are read from the hub working tree, so a task file that exists only on a task branch is not seen; packs are prepared on the default branch
Phase 2: BASE fc0c526
Ruling: a worker that removes its Repos row before landing leaves pack tips behind — accepted as-is, done and status report the commits above the tip — cost if wrong: the owner edits the pack tip by hand once
Note: Phase 2 fix 1: code net +49 (sup_workers.py, sup_digest.py)
Phase 2: complete; fix round 1 (9 addressed), re-review: security PASS, quality 3 open, fixed by the orchestrator in round 2 with tests
Ruling: phase 2 code net 176 against the ceiling of 120 — accepted, the excess is pack_for_land, tips read from the hub commit, close-pack keeping ignored files and Refused handling in the digest, each asked for by a review finding — cost if wrong: the final simplicity review names what to merge
Interface: sup_state.landing_message(hub_dir, branch, task) -> message of the commit with the whole line `Archive: refs/archive/task/<ID>`, or ''  (phase 2; also fixes a 1.17.0 defect: RM-1 matched the commit of RM-10)
Interface: sup_workers.pack_for_land(main, profile|None, task) -> (profile, pack) or (None, None); Refused when a pack with branches holds the task under another profile  (phase 2)
Interface: sup_workers.land_ranges(main, pack, task) -> {slug: (branch, old, new)}; advance_tips(profile, pack, main, hub_commit_message); pack_ahead(hub, pack) -> {slug: (branch, n)}; _pack_wt(checkout, pack); _clean(path); _tip(checkout, branch)  (phase 2)
Interface: sup_digest._pack_repo_problems / _pack_ready_lines / _ahead_lines return lines, never raise Refused; _branch_exists(hub, repo, branch, mp)  (phase 2)
Note: test_sup_watch.py test_an_untrusted_workspace_switches_the_profile_to_headless_and_retries_in_the_same_pass failed once in a full-suite run (worker seen dead between two steps) and passed in 6 runs alone and in the next full run; a timing flake older than this run, to fix at the end
Phase 3: BASE 37d7474
Ruling: next_tasks parses each unstarted task file once per watcher pass — accepted as-is, 0.2 s for 20 tasks against a pass every minute — cost if wrong: a slower pass on a pack of hundreds of tasks
Note: Phase 3 fix 1: code net +15 (sup_workers.py)
Decision: when does the watcher retry a start that was refused for a cause outside the task file — every 5 minutes, without limit, for refusals that did not come from claude — why: the retry starts no session and costs nothing, and a key over every possible cause would miss one — cost if wrong: one refused start-worker call per stuck task every 5 minutes
Note: Phase 3 fix 2: code net -3 (sup_workers.py), sup_watch.py +5/-5
Phase 3: complete; fix rounds 1 and 2 by the implementer, round 3 (3 findings, all in sup_watch._starts) fixed and tested by the orchestrator at the cap
Ruling: phase 3 round-3 fixes were not re-reviewed by the phase reviewer — accepted, each has a test and the final review covers the diff — cost if wrong: a retry-rule defect found at the final review
Ruling: phase 3 code net about 80 against the ceiling of 60 — accepted, the reviewer found no guard left where structure was available — cost if wrong: none beyond size
Interface: sup_workers._edges(profile, pack, hub|None) -> {task: [open blockers]}; Refused, in this order, on an open blocker outside the pack, a cycle, a serial order against an edge; each names `<task> is blocked by <blocker>`  (phase 3)
Interface: sup_workers._blockers(profile, hub|None, task) -> list[str]; _task_meta(root, task) -> dict ({} without a file; Refused when unreadable); task_run.blocker_ids(cell) -> list[str] (phases dropped)  (phase 3)
Interface: sup_watch._starts retries a start refused before claude every 5 minutes (BACKOFF[0]); next_tasks puts tasks of a pack that _edges refuses after the others  (phase 3)
Note: the watcher flake is fixed in phase 3 (the test's fake worker now lives across both steps)
Phase 4: BASE 5e6e330; two lanes (A code, B skill and docs), disjoint files, same working tree
Ruling: phase 4 security finding 4 (quadratic shared-file check) — accepted, a task with thousands of Files entries is not a real input — cost if wrong: a slow ready --pack
Note: Phase 4 fix 1: code net -6 (sup.py -7, sup_workers.py -5, task_lanes.py +6)
Phase 4: complete; fix round 1 by both implementers (18 findings), round 2 by the orchestrator (the slug fallback expression both re-reviews named, with a test; two skill sentences)
Ruling: phase 4 round-2 fix was not re-reviewed — accepted, both reviewers named the exact expression and the test, and the final review covers the diff — cost if wrong: a readiness defect found at the final review
Ruling: phase 4 lib code net about 101 against the ceiling of 80 — accepted, the quality reviewer found the required shape reached (one Repos parser, one task_brief import, one slug helper) and the rest is rule code for the refusals — cost if wrong: none beyond size
Ruling: phase 4 each pack task is parsed twice per check (pack_problems, then _edges) — accepted, closing it adds lines — cost if wrong: a slower ready --pack on a large pack
Interface: sup.pack_problems(profile, pack, hub|None) -> list[str], never raises; lines `<ID>: <problem>` or `pack <name>: <problem>`; `at sup ready --pack <name>` exit 0 `ready` or exit 3; start-pack refuses with the same lines  (phase 4)
Interface: sup.readiness(task_parsed, path, known=None) -> list[str]; sup._brief() -> the task_brief module; sup_workers._task_repos(root, task, meta=None) -> set[str]  (phase 4)
Interface: task_lanes.entry_ok(entry) -> bool; task_lanes.split_entry(entry) -> (slug|None, path); `Files:` entries `path` or `<slug>:path`, no `.` or `..` segment  (phase 4)
Note: under host load (load average 8-10 from other processes) two timing tests failed once each in run-all.sh: hooks test "drift: a peer-check session is silent" (rc 141) and test_run_watch.py test_a_parked_session_is_not_restarted...; both pass alone; older than this run
