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
current_phase: 2
updated: 2026-11-26T14:00:00
---
# Run ledger — supervisor-packs

| Phase | Status | Attempt | Spec | Quality | Security | Open | Commit | Agent |
|---|---|---|---|---|---|---|---|---|
| 1 | committed | 2 | PASS | PASS | PASS | 0 | fc0c526 | — |
| 2 | committed | 3 | PASS | PASS | PASS | 0 | PENDING | — |
| 3 | pending | 0 | — | — | — | 0 | — | — |
| 4 | pending | 0 | — | — | — | 0 | — | — |
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
