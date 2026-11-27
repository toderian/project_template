# Supervisor packs for umbrella tasks: plan

Date: 2026-11-26. Status: revised after the architecture review (plan critic and peer, 2026-11-26); implemented 2026-11-27 (five phases, final review and one fix wave, acceptance trial with real sessions); run state in `docs/_plans/_runs/supervisor-packs/`. Released as 1.18.0; a post-release review and three end-to-end trials led to 1.18.1 (same day). Follows
`docs/specs/2026-11-26-supervisor-session-plan.md` (built, released as 1.17.0).

## Goal

A parent task whose children have an order, write code in sibling repos and need a shared lab can
run as one pack under `at sup`, without the owner doing git by hand and without two workers
damaging each other's work.

Not the goal: running an umbrella like RedMesh RM-276 (tightly ordered, one lab, tooling shared by
every child) faster than its one session does today. See "Fit" at the end.

## Where we are

Two read-only studies on 2026-11-26: the template code, and how the RedMesh hub ran RM-276.

| Gap | What exists | What is missing |
|---|---|---|
| Order between tasks | A serial pack starts the next task after the previous one landed (`sup_workers.py` `next_tasks`). `task_run.py` `open_blockers` reads `Blocked by` for `at task run`. | The supervisor never reads `Blocked by`. The session plan promised it. |
| Sibling repos | Pack fields `branches` and `prs` in the file format; `done_check` checks that a recorded branch exists. | No command writes them. A task worktree has no `.local/repos.map` (ignored file), so a supervised worker has no path to any sibling repo. This blocks every task with code outside the hub. |
| Lab runs | `at sup need` / `grant` / `release`: the worker holds the lease and runs the script itself. Readiness demands a `Resources:` line with a duration. | Nothing says so to the worker. `at sup op` cannot return a result to a worker and a tick ends after 540 s, so it is not the tool for a gate. |
| Preparing a pack | `at sup ready <ID>` per task; `agents-core:unattended-run` writes the unattended section. | No pack-level check (edges, repos, resources). No skill that takes a parent task to a startable pack. `Files:` entries have no way to name a sibling repo. |
| Local files | `land` keeps ignored files of a removed worktree under `kept/<ID>`. | Evidence and bindings (`.no-commit/`, `.local/`) belong to the pack, not to one task; a new task worktree starts without them. |
| Generated ledgers | `at sup land` takes the hub's side of `_active.md` and `_done.md` and rebuilds them. | Nothing: a conflict in an area page is hand-written text and stops the landing on purpose. |

Decided against, with the reason:

- Phase ranges in a pack (`RM-281:1`). A landing of an open task breaks "landed means closed out"
  in seven modules. The task convention already says a separately ordered unit is a task
  (`todo-convention.md`); the fix is to split the task.
- One sibling worktree per task, merged into the pack branch at landing. It makes `land` a
  transaction over several repos with half-landed states. Tasks that share a repo run one after
  another instead.
- A gate run by the watcher between tasks. It is a second scheduler, runs for tens of minutes
  inside a synchronous step, and its output has no reader. The gate is a check of a task.
- `at sup pack --from-parent`. The parent's order is prose and the `Parent` row is not in the
  task format.

## Phases

Tests are stdlib `unittest` under `scripts/tests/`, run by `scripts/tests/run-all.sh`. Each phase
ends with the touched `test_sup_*.py` files; the full suite runs once per phase before the commit.

Terms used below. A **pack repo** is a key of the pack's `branches`: a slug from
`.config/repos.project.md`. Its **checkout** is the path the hub's `.local/repos.map` gives for the
slug; its **pack worktree** is `<checkout>-<pack>`. A key with no line in the map resolves, as in
1.17.0, to the directory of that name beside the hub, so a pack written by 1.17.0 (`branches: {}`
or directory names) keeps working and `test_sup_digest.py` keeps its case. The profile's `repos`
list (absolute paths the supervisor may read) is not changed and not used for this.

#### Phase 1: Pack branches, pack worktrees and the worker's map

- Files: `plugins/agents-core/lib/sup_workers.py`, `plugins/agents-core/lib/sup_state.py`,
  `plugins/agents-core/lib/sup_guard.py`, `scripts/tests/test_sup_workers.py`,
  `scripts/tests/test_sup_guard.py`. Ceiling: 150 code lines.
- Facts to confirm before any code, with one real headless session in a scratch hub that has a
  repo registry and one sibling repo: (a) does a worker on `task/<ID>` stop at the default-branch
  rule of `agents-core:execute-plan`; (b) can it write and commit in a directory outside its cwd
  under the worker's permission mode with no added directory. If (a) fails, this phase adds the
  supervised-worktree case to that skill and to the seed `AGENTS.md`. If (b) fails,
  `session_flags` adds the pack worktrees with `--add-dir`. Both results go to
  `docs/meta/2026-11-26-supervisor-facts.md`.
- One reader for the map (`slug=path` lines) and for the registry slugs; a slug not in the
  registry, or with no path in the map, is refused by name.
- `at sup pack <name> <ID>... --branch <slug>=<branch>` (repeatable) records `branches`. New
  behaviour: a pack written again without `--branch` keeps the recorded ones. The guard's main
  table allows `--branch` with a new value class (`slug=branch`, both from the safe set).
- `at sup start-pack` creates, per pack repo, the branch from the repo's integration branch (or
  attaches to an existing one) and the pack worktree. It refuses when the path exists and is not
  that worktree on that branch. The git work runs before the state lock is taken.
- `at sup start-worker` writes `.local/repos.map` in the task worktree: each pack repo points at
  its pack worktree, every other slug at the hub's entry. It records the tip of each pack repo the
  task names as `sibling_base` in the worker row. The worker prompt gains one sentence: code for a
  sibling repo goes to the path in the map, one commit per phase, on the branch checked out there;
  no branch is created, nothing is pushed.
- `next_tasks` does not offer a task while another task of the pack that names the same pack repo
  in its `Repos` row has a worker row and has not landed.
- Checks: `start-pack` creates branch and worktree and is safe to run twice; the written map
  resolves; two tasks on one repo are never offered together, and the second is offered after the
  first landed; the guard accepts `--branch a-b=feat/x` and refuses a value with a metacharacter.

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

#### Phase 5: Lab runs and linked local paths

- Files: `plugins/agents-core/lib/sup_workers.py`, `plugins/agents-core/lib/sup.py`,
  `plugins/agents-core/lib/sup_tick.py` (`init` keeps the new key),
  `plugins/agents-tasks/skills/supervise/SKILL.md`,
  `plugins/agents-tasks/skills/supervise/assets/profile.json`,
  `scripts/tests/test_sup_workers.py`, `scripts/tests/test_sup_land.py`,
  `scripts/tests/test_sup_tick.py`. Ceiling: 60 code lines, 25 skill lines.
- Session-plan decisions this touches. D21 (built) is about the supervisor: its lab scripts run
  only through `at sup op`. It stays. A worker that holds a lease it got with `at sup need` runs
  commands itself; that is the built behaviour of the session plan's "A resource" paragraph, and
  D20 says nothing in `at sup` fences a worker. This phase only writes it into the worker prompt.
- Worker prompt: for a resource, run its script yourself while you hold the lease, then release.
- Skill text, the contract of a lab script in a hub: absolute path, arguments only, exit 0 means
  pass, its own timeout below the lease minutes, a fresh output directory per attempt, a separate
  restore script, last lines as the summary plus a log path. A gate is the `Checks:` line of the
  step's last phase; a gate that must test landed state is a one-phase task of its own.
- Profile key `local`: a list of relative paths, each ignored by git in the hub (checked with
  `git check-ignore`), no `..`. Absent in a 1.17.0 profile, which means empty. `start-worker`
  creates the hub path as a directory when it is missing and its name ends in `/`, then makes a
  symbolic link at the same relative path in the task worktree. When something that is not that
  link already exists there, `start-worker` refuses and names it. At landing `kept_ignored` skips
  an entry only while it still is a symbolic link that resolves to the hub path; anything else at
  that path (a tool replaced the link with a file) moves to `kept/<ID>` like any ignored file.
- Generated ledgers: nothing to build. `squash_and_commit` already takes the hub's side of
  `_active.md` and `_done.md` and rebuilds them (`GENERATED`, tested in `test_sup_land.py`); a
  conflict in an area page is hand-written text and still stops the landing with the file named.
- First real run of the lease path: one headless worker with `need`, a granted lease, a script,
  `release`, in a scratch hub. The result goes to the facts file.
- Checks: a linked path is present in the task worktree and its content is in the hub after the
  landing; a real file that replaced a link is in `kept/<ID>`; a pre-existing real directory
  refuses the start; `init` of a profile with `local` keeps it and one without it loads.

## Order

Phases 1 and 2 first: without them no task with sibling code can run. Phase 3 next, Phase 4 needs
1 and 3, Phase 5 is independent of 3 and 4. One release at the end, after a trial with real
sessions in a scratch hub that has a repo registry and one sibling repo.

## Hub work (RedMesh), not part of this repo

- A script for the node code swap on the lab nodes (record the commit, check the tree is clean,
  switch, restart, restore). Today it is prose in RM-276.
- A gate wrapper over `scan_run.py webapps-run` and `score_webapps.py` that takes base and head
  commits, uses a fresh output directory, and exits non-zero on a must-not violation or a lost
  cell. The part of "pass" that is a judgement stays a line the worker writes in the log.
- Leases named in the profile: the scan target, the two nodes together with the main `edge_node`
  checkout, the tenant. A blackout around the target's daily reboot.
- Preparation of each child with `agents-tasks:prepare-pack`; in a sample of six, none had
  `Files:`, `Checks:`, `Resources:` or an unattended section.

## Acceptance

- A pack of three tasks, two of them with code in one sibling repo and one blocked by another,
  runs to `at sup done` in a scratch hub with real sessions: the sibling branch holds one commit
  per phase in task order, nothing is pushed, the hub has one squash commit per task, and the owner
  typed only `prepare-pack` answers, `start-pack` and `watch start`.
- `at sup ready --pack` refuses that pack when an edge, a resource or a repo branch is missing.
- A worker took a lease, ran a script and released it in that run.

## Fit

After these phases the supervisor suits a parent whose children are mostly independent, or
ordered as whole tasks. It still does not suit a parent whose children edit the same files, write
each other's task files and share one lab for every step: there the work is one stream, and one
session on one batch branch is the cheaper tool.

## Open questions

- A state between "landed" and "done". In the RedMesh hub a task stays open until the owner's
  merge, the release and a rerun. Today the supervised worker archives the task before landing.
  Options: keep that and track the merge in the pack (`prs`), or a `landed, waits for merge` status
  in the task format. Not decided; it changes `agents-tasks:complete-task`.
- Rulings and lab-run lines that every child appends to the parent's files. One file per task,
  joined by a tool, would be merge-safe; not planned here.

## Out of scope

- `at sup push` and opening PRs. The owner pushes.
- More than one supervisor per hub, and packs across hubs.
