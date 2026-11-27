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
current_phase: done
updated: 2026-11-27T03:20:00
---
# Run ledger — supervisor-packs

| Phase | Status | Attempt | Spec | Quality | Security | Open | Commit | Agent |
|---|---|---|---|---|---|---|---|---|
| 1 | committed | 2 | PASS | PASS | PASS | 0 | fc0c526 | — |
| 2 | committed | 3 | PASS | PASS | PASS | 0 | 37d7474 | — |
| 3 | committed | 4 | PASS | PASS | n/a | 0 | 5e6e330 | — |
| 4 | committed | 3 | PASS | PASS | PASS | 0 | 71bf02b | — |
| 5 | committed | 4 | PASS | PASS | PASS | 0 | d1ca3e5 | — |

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
Phase 5: BASE 71bf02b
Ruling: phase 5 spec finding 6 (a manual `at sup land` without a profile moves the link itself to kept/<ID>) — accepted, the hub content is intact and the watcher passes the profile — cost if wrong: a stray link in kept/
Ruling: phase 5 security finding 2 (race between the ignored-file listing and the move at landing) — accepted, workers run as the owner and nothing fences them (D20) — cost if wrong: an outside file relocated into kept/ by a hostile worker
Note: Phase 5 fix 1: code net +19 (sup.py +6, sup_state.py +8, sup_workers.py +5)
Note: Phase 5 fix 2: code net +2 (sup.py), by the orchestrator: the landing guard no longer depends on a profile
Phase 5: code complete; fix round 1 by the implementer, rounds 2 and 3 by the orchestrator (the landing guard); the first real run of the lease path is done with the acceptance trial in step 6
Ruling: phase 5 round-3 fix (a tracked directory turned into a file) was not re-reviewed by the phase reviewer — accepted, the reviewer named the fix, it has a test, and the final review is pointed at the landing guard — cost if wrong: a shape of hub content loss at landing found at the final review
Ruling: phase 5 lib code net about 90 against the ceiling of 60 — accepted, the reviewer judged the growth justified (three guards, each in one place, no flags or retries) — cost if wrong: none beyond size
Interface: sup_state.local_entries(entries, hub, check=True) -> list[str] (ValueError names the entry; check=False = shape rules only); sup_state.profile_local(profile, hub, check=True) -> list[str], [] without the file or key  (phase 5)
Interface: sup_workers._link_local(profile, hub, cwd) -> skipped entries; links only where the task worktree's git ignores the path; Refused otherwise  (phase 5)
Interface: sup.kept_ignored(wt, linked=()) skips only a link that resolves to a `local` hub path; cmd_land refuses before any commit when the branch adds a path on or under something the hub holds untracked, and when a kept destination is a link or lies outside kept/<ID>  (phase 5)
Final: reviews — reviewer 1 FAIL (C1 I1 M7), reviewer 2 unanchored FAIL (C3 I4 M3), simplicity FAIL (I2 M7), peer FAIL (C1 I2); files final-review-*.md
Final: one fix wave — landing (the orchestrator): the merge is computed first with `git merge-tree`, a conflict is refused before the checkout is touched, the guard reads the paths of the merge result, a branch that stops ignoring a hub file is refused, a kept file is never replaced, a `Repos` entry outside the registry is a problem line; the rest (final/findings-1.md, items A-J) by a fresh implementer
Final: the reviewer's data-loss probes (modify/delete on an older base, dropped ignore line with and without a failing hook, directory rename on default) all refuse now and the hub files stay; full suite `run-all: ok` after the wave
Final: acceptance trial with real headless sessions passed (docs/meta/2026-11-26-supervisor-facts.md, last section); it found that a session cannot write through a `local` link without `--add-dir`, fixed in the wave and proven by waking the same worker
Ruling: the fix wave was not re-reviewed (the skill allows one wave) — accepted, every item has a test, the landing items were re-run against the reviewer's own probes — cost if wrong: a defect in accept-tip or the add-dir argv found in use
Ruling: reviewer 2 finding 10 (pack records read without shape checks) — accepted, the files are written only by the tool and `accept-tip` removes the one reason to edit them by hand — cost if wrong: a traceback after a hand edit
Ruling: reviewer 1 finding 3 (no `sibling_base` in the worker row) — accepted, the landing range comes from the pack tips, which give the same range while one task holds a repo at a time — cost if wrong: none
Ruling: reviewer 1 finding 9 and simplicity 4, 7, 8 (`_resources` one caller, `profile_local(check=)`, test header repeats, `_branch_exists`) — left, each saves under 5 lines
Ruling: simplicity 9 (a task archived by hand without a landing counts as open for `_edges`, and as done for `ready --pack`) — left open, it needs one rule chosen on correctness grounds — cost if wrong: such a task blocks its dependants until the owner lands or reorders
Note: with git older than 2.38 the landing guard falls back to the branch diff: a conflict is then found by the merge itself, after it wrote
Note: `--add-dir` with `--bg` workers is not tried on a real session
Decision: push and release are left to the owner; unpushed: 3a36951 and every commit of this run
Note: post-release round (2026-11-27, after 1.18.0): peer, landing reviewer and workers reviewer on the unreviewed fix wave (`post/review-*.md`): 1 critical, 6 important, 3 minor; all fixed; a re-review found 2 regressions and 3 smaller items (`post/re-review.md`), fixed except the item ruled below
Ruling: re-review finding 6 (the assume-unchanged check also refuses a cleanup-only rerun) — left, the refusal names the way out and nothing is lost — cost if wrong: one extra command for the owner
Note: the note above about git older than 2.38 no longer holds: such a git lands only a branch on the default tip
Note: `--add-dir` with `--bg` was tried in the trials: an untrusted added folder refuses the start; the watcher now falls back to headless
