# Brief: supervisor-packs, phase 2

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

#### Phase 2: Landing, `done` and `close-pack` with pack repos

- Files: `plugins/agents-core/lib/sup.py`, `plugins/agents-core/lib/sup_digest.py`,
  `plugins/agents-core/lib/sup_workers.py`, `scripts/tests/test_sup_land.py`,
  `scripts/tests/test_sup_digest.py`, `scripts/tests/test_sup_flow.py`. Ceiling: 120 code lines.
- `at sup land` refuses while a pack worktree the task names has uncommitted changes. It writes
  `<slug> <branch> <base>..<tip>` per pack repo into the body of the hub commit and stores the tip
  as the repo's `landed_tip` in the pack.
- `kept_ignored` skips exactly one file, the generated `.local/repos.map`. Every other ignored
  file, under `.local/` too, still moves to `kept/<ID>`.
- A task that never lands (refused landing, dead worker, stopped) leaves its commits on the pack
  branch above `landed_tip`. The next task on that repo is not offered (Phase 1 rule), and
  `at sup status` names the repo, the task and the count of commits above `landed_tip`. Nothing is
  reset by the tool; the owner restarts the task or resets the branch.
- `at sup done <pack>`: per pack repo the branch must exist, `landed_tip` must be its tip, and the
  pack worktree must be clean; then one line per repo with the branch, the commit count over the
  integration branch and "ready for PR". `_branch_exists` resolves the key as defined above.
- `at sup close-pack` removes a pack worktree only when it is clean and at `landed_tip`; it keeps
  the branch, and names what it left.
- Checks: in the flow test a pack with one sibling repo runs two tasks in order, the second sees
  the first one's sibling commit, the hub commits carry the ranges, `done` names the branch; a
  dirty pack worktree refuses the landing; a commit above `landed_tip` refuses `done`; an ignored
  file under `.local/` other than the map is in `kept/<ID>` after the landing.


## Task-wide acceptance (context, verified after the last phase)


- A pack of three tasks, two of them with code in one sibling repo and one blocked by another,
  runs to `at sup done` in a scratch hub with real sessions: the sibling branch holds one commit
  per phase in task order, nothing is pushed, the hub has one squash commit per task, and the owner
  typed only `prepare-pack` answers, `start-pack` and `watch start`.
- `at sup ready --pack` refuses that pack when an edge, a resource or a repo branch is missing.
- A worker took a lease, ran a script and released it in that run.


## Orchestrator notes

- Work mode: default-branch (`master`), autonomy L1. Do not commit or stage. No new dependency.
- Scope fence: the phase's `Files:` list. Phase 1 is committed as fc0c526; read its code in sup_workers.py first.
- The plan's `landed_tip` of a repo IS `pack["tips"][slug]` (see the Interface lines): `start-pack` wrote the
  first tip, this phase advances it in `at sup land`. A task's range in the hub commit body is
  `<old tips[slug]>..<new tip>`. Do not add a second field.
- "A pack worktree the task names" = `sup_workers._pack_repos(pack, hub, task)` resolved with `_checkout` and
  the `<checkout.name>-<pack name>` rule; put one helper for "pack worktree path of a slug" in sup_workers.py and
  use it from `_pack_worktrees`, land, done and close-pack instead of rebuilding the path.
- `kept_ignored` (sup.py) must skip exactly `.local/repos.map`; any other ignored file under `.local/` still
  moves to `kept/<ID>`.
- The tips update and the hub squash are two steps: say in the report what state a crash between them leaves and
  make the rerun of `at sup land <ID>` converge (the task is landed in the hub, tips must still advance).
- `at sup status` line for commits above the tip: name repo, the task that holds it (`_held`) and the count
  (`git rev-list --count <tip>..<branch>`).
- `close-pack` never deletes a branch and never uses `--force`; it removes a pack worktree only when clean and at
  the tip, else prints what it left and why.
- Keep 1.17.0 behaviour for a pack with empty `branches` in land, done, close-pack and status; the existing
  case in test_sup_digest.py for `branches` keyed by a directory name beside the hub must stay green unedited.
- Run each touched test file as its own process (`python3 scripts/tests/test_sup_land.py` etc.), never one
  combined unittest call and never scripts/tests/run-all.sh. test_sup_flow.py uses a fake claude; read how it
  builds its hub before adding the sibling-repo case.
- Interface: sup_workers._repos(hub) -> ({slug: (default, integration)}, {slug: absolute path}); Refused on a relative map path  (phase 1)
- Interface: sup_workers._checkout(hub, slug, mp) -> Path; pack worktree = <checkout>.parent/<checkout.name>-<pack name>  (phase 1)
- Interface: sup_workers._task_repos(root, task) -> set of slugs; _pack_repos(pack, hub, task); _held(profile, pack, hub, rows) -> {slug: task}  (phase 1)
- Interface: sup_workers._pack_worktrees(profile, pack) -> {slug: tip}, idempotent; _git(path, *args) raises Refused on OSError/timeout; _valid_branch(b)  (phase 1)
- Interface: pack["branches"] {slug: branch}; pack["tips"] {slug: sha} written once by start-pack, phase 2 advances it at landing (this is the plan's `landed_tip`)  (phase 1)

## Report contract

Write the report to docs/_plans/_runs/supervisor-packs/phase-2/report.md: `## Test plan` first (one row per
checklist behaviour -> lowest layer that proves it -> test name), then what changed per file, the real output of
the tests you ran, code lines added per file against the ceiling, and anything left open. End with
`## Status: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED`.
