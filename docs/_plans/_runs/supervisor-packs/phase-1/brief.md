# Brief: supervisor-packs, phase 1

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


## Task-wide acceptance (context, verified after the last phase)


- A pack of three tasks, two of them with code in one sibling repo and one blocked by another,
  runs to `at sup done` in a scratch hub with real sessions: the sibling branch holds one commit
  per phase in task order, nothing is pushed, the hub has one squash commit per task, and the owner
  typed only `prepare-pack` answers, `start-pack` and `watch start`.
- `at sup ready --pack` refuses that pack when an edge, a resource or a repo branch is missing.
- A worker took a lease, ran a script and released it in that run.


## Orchestrator notes

- Work mode: default-branch (`master`), autonomy L1. Do not commit or stage. No new dependency.
- Scope fence: the phase's `Files:` list, nothing else. `sup_state.py` only if the pack record needs a default.
- Facts confirmed by the orchestrator on 2026-11-26 (claude 2.1.332, `claude -p --model haiku --permission-mode auto`
  in a hub worktree): (b) the session wrote a file and committed in a sibling worktree outside its cwd with no
  denial, so `session_flags` needs no `--add-dir`. (a) is settled without a trial by a
  Decision: the worker prompt states that the worker is on `task/<ID>` in a task worktree on purpose and that a
  registry work mode of `default-branch` for the hub does not apply to it; no skill or seed change in this phase.
- `.local/repos.map` line format is `<slug>: <absolute-path>` (colon), `#` comments and blank lines allowed;
  see `load_local_map` in plugins/agents-tasks/skills/task-ledger/scripts/check_repos_config.sh. Registry slugs
  are the first column of the table in `.config/repos.project.md`, pattern `^[a-z][a-z0-9-]*$`.
- The integration branch of a repo is the `Integration branch` column of its registry row; `N/A` or `unknown`
  there means: use the branch checked out in the checkout, and say so in the output.
- The task's `Repos` row is task-file metadata (see plugins/agents-tasks/skills/task-ledger/references/todo-convention.md);
  reuse whatever `sup.py`/`task_run.py` already has to read a metadata row before writing a parser.
- Git calls go through the existing helpers and `_git_env()`/`clean_env` (they strip `GIT_CONFIG_*`); never a shell string.
- A branch name from `--branch` reaches `git` as an argument: refuse one that starts with `-` or fails
  `git check-ref-format --branch`.
- Keep the 1.17.0 behaviour for a pack with empty `branches`: no worktree, no map written, `next_tasks` as before.
- Existing tests in scripts/tests/test_sup_workers.py and test_sup_guard.py must stay green without edits to
  their assertions, unless a test pinned behaviour this phase changes on purpose (say which in the report).
- Run: `python3 -m unittest scripts/tests/test_sup_workers.py scripts/tests/test_sup_guard.py scripts/tests/test_sup_state.py`
  (check how run-all.sh invokes them first). Do not run scripts/tests/run-all.sh.

## Report contract

Write the report to docs/_plans/_runs/supervisor-packs/phase-1/report.md: `## Test plan` first (one row per
checklist behaviour -> lowest layer that proves it -> test name), then what changed per file, the real output of
the tests you ran, code lines added per file against the ceiling, and anything left open. End with
`## Status: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED`.
