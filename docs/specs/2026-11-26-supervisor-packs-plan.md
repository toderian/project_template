# Supervisor packs for umbrella tasks: plan

Date: 2026-11-26. Status: draft, not reviewed, not started. Follows
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
| Generated ledgers | `at sup land` runs under the `hub-ledger` lease. | Parallel task branches that each ran `at ledger sync` conflict in `_active.md`, `_done.md` and the area files. |

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

#### Phase 1: Sibling repos per pack

- Files: `plugins/agents-core/lib/sup_workers.py`, `plugins/agents-core/lib/sup.py`,
  `plugins/agents-core/lib/sup_digest.py`, `plugins/agents-core/lib/sup_watch.py`,
  `scripts/tests/test_sup_workers.py`, `scripts/tests/test_sup_land.py`,
  `scripts/tests/test_sup_digest.py`, `scripts/tests/test_sup_flow.py`.
  Ceiling: 150 code lines plus tests.
- `at sup pack <name> <ID>... --branch <repo-slug>=<branch>` (repeatable) records `branches`. A
  replaced pack keeps them unless they are given again. The slug must be a row of
  `.config/repos.project.md`; the checkout path comes from the hub's `.local/repos.map`.
- `at sup start-pack` creates, per recorded repo, the branch from that repo's integration branch
  (or attaches to an existing one) and one worktree `<repo>-<pack>` beside the checkout. It refuses
  when a path exists and is not that worktree.
- `at sup start-worker` writes `.local/repos.map` in the task worktree: each pack repo points at
  the pack worktree, every other slug at the hub's own entry. The worker prompt gains one
  sentence: code for a sibling repo goes to the path in the map, one commit per phase, on the
  branch that is checked out there; no branch is created, nothing is pushed.
- `next_tasks` never offers two tasks at once whose `Repos` rows share a pack repo.
- `at sup land` refuses while a pack worktree named by the task's `Repos` row has uncommitted
  changes, and writes each sibling branch tip into the body of the hub commit. `kept_ignored`
  skips `.local/`.
- `at sup done <pack>` prints one line per repo: branch, commits over the integration branch,
  "ready for PR". `at sup close-pack` removes clean pack worktrees and keeps the branches.
- Fact to confirm first, with one real session in a scratch hub that has a repo registry: does a
  worker on `task/<ID>` stop at the default-branch rule of `agents-core:execute-plan` (its
  "Never create a branch" and work-mode check)? If yes, this phase adds the supervised-worktree
  case to that skill and to the seed `AGENTS.md`, as the session plan (its line 183) intended.
- Checks: a pack with one sibling repo runs two tasks in order in the flow test, the second sees
  the first one's sibling commit, `done` names the branch; two tasks on one repo are never live
  together; a dirty pack worktree refuses the landing.

#### Phase 2: `Blocked by` in the supervisor

- Files: `plugins/agents-core/lib/sup_workers.py`, `scripts/tests/test_sup_workers.py`. Ceiling: 30
  code lines.
- `next_tasks` skips a task whose `Blocked by` names a task that is neither landed in this profile
  nor archived on the default branch. `at sup pack` refuses a serial pack whose order contradicts
  an edge, and names the edge. The parsing is `task_run.open_blockers`, with "landed" in place of
  "status done".
- A blocker with a phase ("RM-281 Phase 1") counts as the whole task. The readiness check of
  Phase 3 reports it, so the owner splits the task before the run.
- Checks: in a parallel pack a blocked task starts in the watcher pass after its blocker landed
  and not before; a blocker outside the pack that is archived does not block.

#### Phase 3: Pack readiness and the preparation skill

- Files: `plugins/agents-core/lib/sup.py`, `scripts/tests/test_sup_land.py`,
  `plugins/agents-tasks/skills/prepare-pack/SKILL.md` (new),
  `plugins/agents-tasks/skills/supervise/SKILL.md`,
  `plugins/agents-tasks/skills/task-ledger/references/todo-convention.md`,
  `plugins/agents-core/seed/AGENTS.md` (routing rows for `agents-tasks:prepare-pack` and
  `agents-tasks:supervise`), `README.md`, counts in `scripts/tests/test-codex-live.sh` and
  `scripts/tests/test_codex_compat.py`. Ceiling: 60 code lines, 110 skill lines.
- `Files:` entries may carry a repo slug: `edge-node:extensions/x.py`. An entry without a slug is
  a hub path. Readiness accepts a slug only when the task's `Repos` row has it.
- `### Unattended run` and `Resources:` are inherited from the parent task when the child has
  none (the section already is; the line is new).
- `at sup ready --pack <name>`: `readiness` for every task, then: every `Blocked by` is in the
  pack and earlier, or archived; no blocker names a phase; every resource exists in the profile;
  every slug in a `Repos` row or a `Files:` entry has a pack branch; no two tasks that can run
  together share a `Files:` path. Prints `ready` or one line per problem, exit 3.
- `agents-tasks:prepare-pack` (model-invocable; it changes task files only): list the parent's
  open children and stated order; split a child whose phases belong to different steps or to
  different code repos (hand-off to `agents-tasks:add-task`); write `Blocked by`, the `Repos` row,
  `Files:`, `Checks:` and `Resources:` per child; hand off once to `agents-core:unattended-run` for
  the parent's section; propose pack shape and one branch per sibling repo; run
  `at sup ready --pack`; play the pack back to the owner; commit the task edits on the default
  branch; hand off to `agents-tasks:supervise`. Complete when the pack check prints `ready` and
  the owner confirmed the playback.
- Checks: `python3 scripts/build.py --check`; the pack check finds each of its five problems in a
  test; the skill passes the repo's skill validation.

#### Phase 4: Lab runs and pack-local files

- Files: `plugins/agents-core/lib/sup_workers.py` (prompt and `start-worker`),
  `plugins/agents-core/lib/sup.py`, `plugins/agents-tasks/skills/supervise/SKILL.md`,
  `plugins/agents-tasks/skills/supervise/assets/profile.json`,
  `scripts/tests/test_sup_workers.py`, `scripts/tests/test_sup_ask.py`. Ceiling: 50 code lines,
  25 skill lines.
- Worker prompt: for a resource, run its script yourself while you hold the lease, then release.
- Skill text, the contract of a lab script in a hub: absolute path, arguments only, exit 0 means
  pass, its own timeout below the lease minutes, a fresh output directory per attempt, a separate
  restore script, last lines as the summary plus a log path. A gate is the `Checks:` line of the
  step's last phase; a gate that must test landed state is a one-phase task of its own.
- Profile key `local`: a list of ignored paths in the hub (for example `.local/lab.json`,
  `.no-commit/<pack>/`). `start-worker` links each into the task worktree, so bindings and evidence
  live once per hub and survive the worktree. `land` does not move linked paths to `kept/`.
- Generated ledgers: `at sup land` discards the task branch's changes to the ledger files that
  `at ledger sync` writes, and runs the sync once on the default branch after the squash. Fact to
  confirm first: the exact list of generated files, from `sync_todo_ledgers.py`.
- First real run of the lease path, never tried in the three trials: one worker with `need`, a
  granted lease, a script, `release`, in a scratch hub.
- Checks: two parallel tasks that each change a task file land without a ledger conflict; a linked
  local path is present in the task worktree and still in the hub after the landing.

## Order

Phase 1 first: without it no task with sibling code can run. Phase 2 with it or right after (same
function). Phase 3 needs the pack fields of Phase 1. Phase 4 is independent of 2 and 3. One
release after Phases 1 and 2, one after 3 and 4. Each release is followed by one trial with real
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
