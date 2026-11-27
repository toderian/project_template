---
name: supervise
description: "Set up and run a supervisor for a hub's worker sessions: a profile, packs of tasks, a watcher, and an interactive chat that answers worker questions inside the recorded authorisation. Use when a human wants several task sessions run in parallel from one repo with their questions and lab-resource requests handled, or asks to start, stop, trial or clean up a supervisor."
disable-model-invocation: true
metadata:
  pack: task-management
---

# Supervise

## Purpose

A supervisor runs worker sessions (one per task, each in its own worktree) and handles what stops them: questions,
resource requests, finished tasks. It writes no code. Stdlib code does the scheduling; a short LLM session (a tick)
judges only events that need it; the owner talks to the same agent in a chat. All state lives on the host under
`at sup`, so a tick can be killed and a chat cleared without loss. Task format: `agents-tasks:task-ledger`.

Use this when tasks are prepared (readiness checked, `Authorised` and `Defaults` lines written) and the owner wants
them run in parallel. Do not use it for one task: run `agents-core:execute-plan`.

## Set up, in this order

1. Copy `assets/profile.json` and fill it: repos, resources (`name`, default `minutes`, `auto`, and `scripts`: the
   lab wrapper scripts of that resource as absolute paths), session `cap` and `land` mode, and `local` (below).
2. `at sup init --profile <p> --hub <hub> --from <profile.json>` (the owner's shell or chat; a worker or tick is
   refused). It records the hub in the profile's config, so later commands need no `--hub`, and writes nothing into
   the hub. Everything goes to `${AGENTS_SUP_DIR:-~/.local/state/agents-template/sup}/<p>/conf/` (mode 0700):
   `settings.json`, `tables.json` (0600), `profile.json` and `.claude/agents/<p>-supervisor.md`, `-adviser.md`,
   `-operator.md`. Existing files are refused without `--force`.
3. Review the generated files. Check that the supervisor's tool list has no Edit or Write, that `settings.json` runs
   `/bin/bash <path>/sup-guard.sh` as its PreToolUse hook, and that `tables.json` holds only the operator's `at sup op`
   rule, `at lease list` and an empty adviser table: the supervisor's own commands are the guard's built-in table
   (`DEFAULT_MAIN` in `sup_guard.py`), which the file cannot override.
4. Prepare the tasks with `agents-tasks:prepare-pack`. Then `at sup pack <name> <TASK>... [--parallel]
   [--branch <slug>=<branch>]...` for each pack, `at sup ready --pack <name>` (prints `ready`, or one line per problem
   and exits 3), then `at sup start-pack <name>`, which runs the same check and refuses on a problem.
   - A task with code in a sibling repo needs `--branch` for that repo's slug. `start-pack` makes the branch off the
     repo's integration branch and a pack worktree `<checkout>-<pack>`, and records its tip. Tasks that share a pack
     repo never run together.
   - Each task worktree gets `.local/repos.map` with the pack repos at their pack worktree. The worker commits to
     them, one commit per phase. Nothing is pushed.
   - `Blocked by` in a task file orders the pack: a task starts after its blockers landed, and the digest shows
     `waits for <ID>`. A blocker outside the pack, a cycle or a serial order against an edge is refused.
   - A lab script of a resource, in the hub: an absolute path; arguments only; exit 0 means pass; its own timeout
     below the lease minutes; a fresh output directory per attempt; a separate restore script; the last lines are
     the summary and a log path. A worker that holds the lease runs it itself; the supervisor only through `at sup op`.
   - A gate is the `Checks:` line of the step's last phase. A gate that must test landed state is a one-phase task
     of its own.
   - `local` in the profile lists hub paths a task worktree shares, e.g. `"local": ["lab-results/", "data/cache.db"]`.
     Each is relative, has no `..`. Write `lab-results`, not `lab-results/`, in `.gitignore`: the task worktree holds
     a link, not a directory. The line must be in the branch the task starts from. A trailing `/` in `local` marks a
     directory, which `start-worker` creates in the hub. `start-worker` links each path into the
     task worktree and refuses when something else is there. At landing the link goes; a real file in its place is
     kept in `kept/<ID>`. A file entry that is not in the hub is skipped. A file at the hub root is linked but not
     writable by the worker (its parent is the whole hub); put it in a directory to make it writable.
5. Worker mode (config key `worker_mode`): `bg` (workers as background sessions) needs the hub opened once
   interactively with `claude` so the workspace is trusted; `headless` (`claude -p`) needs nothing. A worker must
   arm the run guard (`at run-guard arm`, as `agents-core:execute-plan` does when it opens a run): without it its
   stops, parks and DONE never reach the supervisor.
   Then `at sup watch start --profile <p>` (the owner's shell): the watcher starts ready tasks in a running pack, grants
   `auto` resources, and starts a tick (`at sup tick`) on an event that needs judgement. It tells the owner by itself
   (a queue entry and `at notify`) about a dead worker, a refused start or landing, an owed or overdue lease, paused
   ticks and a worker that stops BLOCKED or GAVE_UP, with or without ticks.
6. `at sup chat --profile <p>` (the owner's shell): the owner's interactive session; its opening message is the
   digest. Its working directory is the `conf/` directory, not the hub, so Claude Code asks you once to trust that
   directory: accept it. The supervisor reads hub files by absolute path.

## The owner's commands

- In chat: "status" (the digest, the queue first), answers to the queue (`at sup answer <Q-id> '<text>' --owner`),
  standing instructions (recorded at once with `at sup instruct`), `pack`, `start-pack`, `pause-pack`,
  `close-pack`, `order`, `cap`. Only the chat session (its token) runs these from a supervisor. Outside a supervisor,
  any session but a worker may also run `pack`: it writes the pack record and starts nothing.
- In chat, anything the supervisor cannot do itself (git, a shell, reading code, cleaning a checkout, stopping a
  stray session): it hands the ask to a topic session with `at sup delegate <topic> '<ask>'` instead of handing it
  back to you. A topic is a long-lived bg session (`<profile>-topic-<name>`) that keeps its context between asks on
  the same topic and keeps a notes file; `--fresh` restarts it from the notes when its context is long. At most
  `topic_cap` (config, default 3) run at once. `at sup topics` shows each topic's state and last result line,
  `at sup topic-log <topic>` its recent output, `at sup stop-topic <topic>` stops it. Topics do not push or merge.
- The watcher stops every bg session named `<profile>-<TASK>` or `<profile>-topic-<name>` that sup does not track
  (`at sup reap`, also by hand with `--dry-run`), so a lost start never leaves two workers in one worktree.
- `at sup board` writes and prints `board.md`: digest plus the whole queue.
- Agent view: watch a worker or approve a permission prompt; no supervisor can.
- Owner's shell only: `at sup init|tick|chat`, `at sup watch start|stop|once`, `at lease clear`, and any `git push`.
  No LLM pushes.
- Landing a task squash-merges it into the hub and records, in the hub commit, the commit range it added to each pack
  repo. The owner reviews the branches and pushes them.
- When a pack is finished: `at sup done <pack>` (exit 0 when every task is landed and nothing is live; it lists each
  pack branch that is ready for PR), then `at sup close-pack <pack>`. `close-pack` removes the pack worktrees and
  keeps every branch. It keeps a worktree that has uncommitted changes, is not at the landed tip or holds ignored
  files, and says why.
  When a pack branch has a commit above its landed tip or moved off it (an owner fixup), `done` exits 3 and
  `close-pack` keeps the worktree: the owner runs `at sup accept-tip <pack> <slug>` in chat to take the branch head as
  the landed tip.

## What the supervisor may decide

- Answer a worker only when the answer follows from the task file, the owner's standing instructions or a recorded
  decision; each answer is a `Decision: [sup-<n>]` line naming its source. Never above the repo's `Autonomy max`.
- Grant or deny a resource request (`at sup grant <TASK> <resource>`, `at sup deny <TASK> <resource> '<reason>'`);
  leave anything else for the owner with `at sup escalate '<text>' [--task <TASK>] [--blocking]`; land a task that
  passed the done check; start the next ready task. Lab scripts run only through the operator's `at sup op`.
- It has no `git`, `gh` or `claude` command and no `at lease take|release`: work that needs them goes to a topic
  (`at sup delegate`, chat only), never back to the owner as shell steps; it may not edit files, push, clear a
  lease, change instructions or pack controls from a tick, or run any command outside the guard's tables.
  Everything else stays in the owner's queue.

## What the guard does and does not protect

A worker runs under the same user as the state directory, so nothing in `at sup` stops a worker: the chat token, the
guard and `by: owner` marks stop only the guarded supervisor (a tick or the chat) and honest mistakes, and
`touch.log` is a record, not proof. Worker text never enters a tick prompt: events are ids only, and the supervisor
reads questions itself with `at sup queue`, as data.

## Trial arms

- Arm A, no LLM: `at sup watch start --no-tick`. The owner works from `at sup status`, the queue and the agent view.
- Arm B: `at sup watch start` with ticks, same kind of packs. Compare per event with `at sup measure`: owner
  touches, time to the worker's next step, cost (`ticks.jsonl` has each tick's cost), share of questions answered.
  Read every `Decision: [sup-` line afterwards and overrule what is wrong.

## Stop and clean up

- `at sup watch stop --profile <p>`. A tick in flight can be killed: the cursor moves only when it ends with
  `TICK done:`, so the next tick repeats the events.
- Remove a profile by deleting `${AGENTS_SUP_DIR:-~/.local/state/agents-template/sup}/<p>/` (its `conf/` included)
  after `at sup close-pack` on each pack. Chat tokens expire after 12 hours.

## Completion criteria

- `at sup init` wrote every file under `conf/` and `at sup chat --print-command` shows the settings file and the agent.
- A tick on a test event ends with `TICK done:` and moves the cursor; a failing tick leaves it.
- The owner can read each answer the supervisor gave in the queue or the inbox and overrule it.
