# Brief: supervisor-packs, phase 4

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

#### Phase 4: Pack readiness and the preparation skill

- Files: `plugins/agents-core/lib/sup.py`, `plugins/agents-core/lib/task_lanes.py`,
  `plugins/agents-core/lib/sup_guard.py`, `scripts/tests/test_sup_land.py`,
  `scripts/tests/test_sup_guard.py`, the test file of `task_lanes.py`,
  `plugins/agents-tasks/skills/prepare-pack/SKILL.md` (new),
  `plugins/agents-tasks/skills/supervise/SKILL.md`,
  `plugins/agents-tasks/skills/task-ledger/references/todo-convention.md`,
  `plugins/agents-core/seed/AGENTS.md` (routing rows for `agents-tasks:prepare-pack` and
  `agents-tasks:supervise`), `README.md`, skill counts in `scripts/tests/test-codex-live.sh` and
  `scripts/tests/test_codex_compat.py`. Ceiling: 80 code lines, 110 skill lines.
- `Files:` entries may carry a repo slug: `edge-node:extensions/x.py`. `task_lanes.fence` accepts
  the form and returns it unchanged; an entry without a slug is a path in the task's own checkout,
  as today. The lane planner of `at task run --lanes` compares entries as strings, so two entries
  overlap only inside one repo. Readiness accepts a slug only when the task's `Repos` row has it.
- No new inheritance from the parent task: `Resources:` is written per child by the skill.
- `at sup ready --pack <name>` (allowed in the guard's main table): `readiness` for every task,
  then: the three edge rules of Phase 3; no blocker names a phase; every resource exists in the
  profile; every slug in a `Repos` row or a `Files:` entry is a pack repo; no two tasks that can
  run together share a `Files:` entry. Prints `ready` or one line per problem, exit 3.
  `at sup start-pack` runs the same check and refuses on a problem.
- `agents-tasks:prepare-pack` (model-invocable; it changes task files only): list the parent's
  open children and stated order; split a child whose phases belong to different steps or to
  different code repos (hand-off to `agents-tasks:add-task`); write `Blocked by`, the `Repos` row,
  `Files:`, `Checks:` and `Resources:` per child; hand off once to `agents-core:unattended-run` for
  the parent's section; propose pack shape and one branch per sibling repo; run
  `at sup ready --pack`; play the pack back to the owner; commit the task edits on the default
  branch; hand off to `agents-tasks:supervise`. Complete when the pack check prints `ready` and
  the owner confirmed the playback.
- Checks: `python3 scripts/build.py --check`; each problem of the pack check has a test; a
  slug-qualified entry passes `fence` and `../` after a slug is refused; the skill passes the
  repo's skill validation.


## Task-wide acceptance (context, verified after the last phase)


- A pack of three tasks, two of them with code in one sibling repo and one blocked by another,
  runs to `at sup done` in a scratch hub with real sessions: the sibling branch holds one commit
  per phase in task order, nothing is pushed, the hub has one squash commit per task, and the owner
  typed only `prepare-pack` answers, `start-pack` and `watch start`.
- `at sup ready --pack` refuses that pack when an edge, a resource or a repo branch is missing.
- A worker took a lease, ran a script and released it in that run.


## Orchestrator notes

- Work mode: default-branch (`master`), autonomy L1. Do not commit or stage. No new dependency.
- Phases 1-3 are committed (fc0c526, 37d7474, 5e6e330). This phase runs as two parallel lanes with disjoint files:
  LANE A (code): plugins/agents-core/lib/sup.py, plugins/agents-core/lib/task_lanes.py,
  plugins/agents-core/lib/sup_guard.py, plugins/agents-core/lib/sup_workers.py (only to call the pack check from
  `cmd_start_pack`), scripts/tests/test_sup_land.py, scripts/tests/test_sup_guard.py, scripts/tests/test_sup_workers.py,
  the test file of task_lanes.py (find it with grep).
  LANE B (skill and docs): plugins/agents-tasks/skills/prepare-pack/SKILL.md (new),
  plugins/agents-tasks/skills/supervise/SKILL.md, plugins/agents-tasks/skills/task-ledger/references/todo-convention.md,
  plugins/agents-core/seed/AGENTS.md, README.md, the skill counts in scripts/tests/test-codex-live.sh and
  scripts/tests/test_codex_compat.py, and whatever `python3 scripts/build.py` generates for the new skill.
- CLI contract both lanes share (lane A builds it, lane B documents it, neither changes it):
  `at sup ready --pack <name> [--profile P]` prints `ready` and exits 0, or one line per problem and exits 3.
  Problem lines are `<TASK-ID>: <problem>` for a task problem and `pack <name>: <problem>` for a pack problem.
  `at sup ready <TASK-ID>` keeps its present behaviour. `at sup start-pack <name>` runs the same check and refuses.
  Existing from phases 1-3: `at sup pack <name> <ID>... [--parallel] [--branch <slug>=<branch>]...`,
  `at sup start-pack`, `at sup done <pack>`, `at sup close-pack`, `at sup status`.
- The pack check = `readiness` of every task, then, in this order: the edge rules through `sup_workers._edges`
  (its Refused text is one problem line); a `Blocked by` cell that names a phase (`RM-281 Phase 1`:
  `task_run.blocker_ids` drops the phase, so test the raw cell); every `Resources:` name exists in the profile
  (reuse what `readiness` already does for one task, do not check twice); every slug in a `Repos` row other than
  the hub's own slug, and every slug prefix in a `Files:` entry, is a key of the pack's `branches`; no two tasks
  that can run together share a `Files:` entry. "Can run together" = a parallel pack, the two tasks do not block
  each other directly or through other tasks, and they do not share a pack repo (phase 1 already serialises
  those). A serial pack never has two together.
- `Files:` entry forms: `path/in/own/checkout` (as today) and `<slug>:path/in/that/repo`. `task_lanes.fence`
  accepts both and returns the entries unchanged; `..` in any path part and an empty path after the slug are
  refused; the slug matches `^[a-z][a-z0-9-]*$`. Readiness refuses a slug the task's `Repos` row does not have.
  Check every caller of `fence` and `PATH_RE` (grep) so the lane planner of `at task run --lanes` and the scope
  fence it hands to implementers still work with a `slug:path` entry.
- "The hub's own slug": the registry row whose map path is the hub; if none can be determined, a slug without a
  pack branch is a problem only when the map gives it a path other than the hub.
- A 1.17.0 pack (no branches, no `Blocked by`, plain `Files:`) must give the same `ready`/`start-pack` result as
  `at sup ready <ID>` gives per task today; `start-pack` newly refusing an unready pack is intended, say so in the reply.
- The supervisor session's guard (sup_guard.py DEFAULT_MAIN): `at sup ready` currently takes one task id; allow
  `--pack <name>` with the pack-name class already used by `at sup start-pack`.
- Skill rules for lane B: read "## Writing skills" in the repo's AGENTS.md and one neighbouring skill
  (plugins/agents-tasks/skills/supervise/SKILL.md) as the model; every skill is named by its full
  `plugin:skill` id; the description is harness-neutral ("Use when …"), at most 1,024 characters; no
  `disable-model-invocation` (the skill only edits task files); hand off to a peer skill once, never describe how
  the peer works; the task format belongs to `agents-tasks:task-ledger` (point at it). README.md has a table of
  skills per plugin and counts; grep for the number of skills (75) in the two test files and the README.
- Interface: sup_workers._repos(hub) -> ({slug: (default, integration)}, {slug: absolute path}); Refused on a relative map path  (phase 1)
- Interface: sup_workers._checkout(hub, slug, mp) -> Path; pack worktree = <checkout>.parent/<checkout.name>-<pack name>  (phase 1)
- Interface: sup_workers._task_repos(root, task) -> set of slugs; _pack_repos(pack, hub, task); _held(profile, pack, hub, rows) -> {slug: task}  (phase 1)
- Interface: sup_workers._pack_worktrees(profile, pack) -> {slug: tip}, idempotent; _git(path, *args) raises Refused on OSError/timeout; _valid_branch(b)  (phase 1)
- Interface: pack["branches"] {slug: branch}; pack["tips"] {slug: sha} written once by start-pack, phase 2 advances it at landing (this is the plan's `landed_tip`)  (phase 1)
- Interface: sup_state.landing_message(hub_dir, branch, task) -> message of the commit with the whole line `Archive: refs/archive/task/<ID>`, or ''  (phase 2; also fixes a 1.17.0 defect: RM-1 matched the commit of RM-10)
- Interface: sup_workers.pack_for_land(main, profile|None, task) -> (profile, pack) or (None, None); Refused when a pack with branches holds the task under another profile  (phase 2)
- Interface: sup_workers.land_ranges(main, pack, task) -> {slug: (branch, old, new)}; advance_tips(profile, pack, main, hub_commit_message); pack_ahead(hub, pack) -> {slug: (branch, n)}; _pack_wt(checkout, pack); _clean(path); _tip(checkout, branch)  (phase 2)
- Interface: sup_digest._pack_repo_problems / _pack_ready_lines / _ahead_lines return lines, never raise Refused; _branch_exists(hub, repo, branch, mp)  (phase 2)
- Interface: sup_workers._edges(profile, pack, hub|None) -> {task: [open blockers]}; Refused, in this order, on an open blocker outside the pack, a cycle, a serial order against an edge; each names `<task> is blocked by <blocker>`  (phase 3)
- Interface: sup_workers._blockers(profile, hub|None, task) -> list[str]; _task_meta(root, task) -> dict ({} without a file; Refused when unreadable); task_run.blocker_ids(cell) -> list[str] (phases dropped)  (phase 3)
- Interface: sup_watch._starts retries a start refused before claude every 5 minutes (BACKOFF[0]); next_tasks puts tasks of a pack that _edges refuses after the others  (phase 3)

## Report contract

Write the report to docs/_plans/_runs/supervisor-packs/phase-4/report.md: `## Test plan` first (one row per
checklist behaviour -> lowest layer that proves it -> test name), then what changed per file, the real output of
the tests you ran, code lines added per file against the ceiling, and anything left open. End with
`## Status: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED`.
