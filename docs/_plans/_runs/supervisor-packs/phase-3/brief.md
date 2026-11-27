# Brief: supervisor-packs, phase 3

Plan: docs/specs/2026-11-26-supervisor-packs-plan.md (read "Where we are" and "Decided against" for context).
Repo: a plugin marketplace; the supervisor is `at sup` in plugins/agents-core/lib/sup*.py (python3, stdlib only).

## Context for all phases

Tests are stdlib `unittest` under `scripts/tests/`, run by `scripts/tests/run-all.sh`. Each phase
ends with the touched `test_sup_*.py` files; the full suite runs once per phase before the commit.

Terms used below. A **pack repo** is a key of the pack's `branches`: a slug from
`.config/repos.project.md`. Its **checkout** is the path the hub's `.local/repos.map` gives for the
slug; its **pack worktree** is `<checkout>-<pack>`. A key with no line in the map resolves, as in
1.17.0, to the directory of that name beside the hub, so a pack written by 1.17.0 (`branches: {}`
or directory names) keeps working and `test_sup_digest.py` keeps its case. The profile's `repos`
list (absolute paths the supervisor may read) is not changed and not used for this.


## This phase

#### Phase 3: `Blocked by` in the supervisor

- Files: `plugins/agents-core/lib/sup_workers.py`, `plugins/agents-core/lib/task_run.py` (the
  blocker ids as a function of their own, `open_blockers` built on it),
  `plugins/agents-core/lib/sup_digest.py`, `scripts/tests/test_sup_workers.py`,
  `scripts/tests/test_sup_digest.py`. Ceiling: 60 code lines.
- `next_tasks` skips a task whose `Blocked by` names a task that is neither landed in this profile
  nor archived on the default branch. A blocker with a phase ("RM-281 Phase 1") counts as the
  whole task.
- No silent wait: `at sup pack` and `at sup start-pack` refuse, naming the edge, when a blocker is
  open and outside the pack, when a serial order contradicts an edge, or when the edges form a
  cycle. So a blocked task in a started pack always has a blocker that the pack will land.
  `at sup status` shows `waits for <ID>` on such a task.
- Checks: in a parallel pack a blocked task is offered after its blocker landed and not before; an
  archived blocker outside the pack does not block; each of the three refusals has a test.


## Task-wide acceptance (context, verified after the last phase)


- A pack of three tasks, two of them with code in one sibling repo and one blocked by another,
  runs to `at sup done` in a scratch hub with real sessions: the sibling branch holds one commit
  per phase in task order, nothing is pushed, the hub has one squash commit per task, and the owner
  typed only `prepare-pack` answers, `start-pack` and `watch start`.
- `at sup ready --pack` refuses that pack when an edge, a resource or a repo branch is missing.
- A worker took a lease, ran a script and released it in that run.


## Orchestrator notes

- Work mode: default-branch (`master`), autonomy L1. Do not commit or stage. No new dependency.
- Scope fence: the phase's `Files:` list. Phases 1 and 2 are committed (fc0c526, 37d7474); read `next_tasks`,
  `_held`, `_refusal`, `cmd_pack`, `cmd_start_pack` in sup_workers.py first.
- `task_run.open_blockers` (task_run.py:1184) is the parser to build on: split out "the task ids a task's
  `Blocked by` row names" as its own function and keep `open_blockers`' behaviour and tests unchanged.
- "Landed" for the supervisor is the existing `_landed(profile, task, hub)`; "archived on the default branch" is a
  task file under `docs/tasks_manager/_todos_archived/` in the hub working tree.
- One function decides "the open blockers of this task in this pack" and serves `next_tasks`, `_refusal` (a hand
  `at sup start-worker` must refuse too, naming the blocker), the three refusals of `pack`/`start-pack`, and the
  `waits for <ID>` text of `at sup status`. No second copy of the rule.
- The three refusals: (1) a blocker that is open and not in the pack; (2) a serial pack whose order puts a task
  before its blocker; (3) a cycle among the pack's tasks. Each names the edge as `<task> is blocked by <blocker>`.
  A parallel pack only needs (1) and (3).
- Task files are read from the hub working tree. A task of the pack with no task file has no blockers.
- The digest is fed to an LLM tick: any new text in it goes through the existing `_word`/`_ptask` helpers of
  sup_digest.py (prompt mode), like the section phase 2 added.
- Keep 1.17.0 behaviour for a pack whose tasks have no `Blocked by` rows: same offers, same output.
- Run each touched test file as its own process (`python3 scripts/tests/test_sup_workers.py`); also run
  the test file that covers task_run.py's `open_blockers` (find it with grep). Never scripts/tests/run-all.sh.
- Interface: sup_workers._repos(hub) -> ({slug: (default, integration)}, {slug: absolute path}); Refused on a relative map path  (phase 1)
- Interface: sup_workers._checkout(hub, slug, mp) -> Path; pack worktree = <checkout>.parent/<checkout.name>-<pack name>  (phase 1)
- Interface: sup_workers._task_repos(root, task) -> set of slugs; _pack_repos(pack, hub, task); _held(profile, pack, hub, rows) -> {slug: task}  (phase 1)
- Interface: sup_workers._pack_worktrees(profile, pack) -> {slug: tip}, idempotent; _git(path, *args) raises Refused on OSError/timeout; _valid_branch(b)  (phase 1)
- Interface: pack["branches"] {slug: branch}; pack["tips"] {slug: sha} written once by start-pack, phase 2 advances it at landing (this is the plan's `landed_tip`)  (phase 1)
- Interface: sup_state.landing_message(hub_dir, branch, task) -> message of the commit with the whole line `Archive: refs/archive/task/<ID>`, or ''  (phase 2; also fixes a 1.17.0 defect: RM-1 matched the commit of RM-10)
- Interface: sup_workers.pack_for_land(main, profile|None, task) -> (profile, pack) or (None, None); Refused when a pack with branches holds the task under another profile  (phase 2)
- Interface: sup_workers.land_ranges(main, pack, task) -> {slug: (branch, old, new)}; advance_tips(profile, pack, main, hub_commit_message); pack_ahead(hub, pack) -> {slug: (branch, n)}; _pack_wt(checkout, pack); _clean(path); _tip(checkout, branch)  (phase 2)
- Interface: sup_digest._pack_repo_problems / _pack_ready_lines / _ahead_lines return lines, never raise Refused; _branch_exists(hub, repo, branch, mp)  (phase 2)

## Report contract

Write the report to docs/_plans/_runs/supervisor-packs/phase-3/report.md: `## Test plan` first (one row per
checklist behaviour -> lowest layer that proves it -> test name), then what changed per file, the real output of
the tests you ran, code lines added per file against the ceiling, and anything left open. End with
`## Status: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED`.
