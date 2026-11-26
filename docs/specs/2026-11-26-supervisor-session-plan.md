# Supervisor: plan

Date: 2026-11-26. Status: draft, version 2. Version 1 passed four architecture review rounds and was
then found not ready by a second research round; this version is the reshape the owner agreed to
(D6–D17). One independent review of version 2 said "revise first"; its findings are applied below
and the result has not been reviewed again. History is in the last section.

## Goal

The owner talks to one orchestrator per scope, the supervisor. The supervisor writes no code. It
manages the tasks of its scope: it prepares them, orders them, starts and stops the worker sessions
that execute them, shares single-holder resources between workers, answers their questions inside a
recorded authorisation, and brings the rest to the owner in one queue. The owner stops running
working sessions by hand and stops checking task status across repos.

A downstream repo defines its supervisors as profiles. One hub can run several, for example one for
RedMesh work and one for EdgeGuard work.

## Where we are

Evidence: the usage profile of 2026-11-26 (`project_r1_redmesh/.no-commit/agent-usage-profile-2026-11-26/`),
two research rounds of the same day, and a dry run of version 1 on the RedMesh hub's real tasks.

What the owner does by hand today (dev machine, 16 days):

| Manual work | Seen as |
|---|---|
| Checks status, open PRs, merges and pins across four repos | 9 of 48 owner messages in one session were status questions; "open prs" waited 37 minutes |
| Notices idle, blocked or stopped sessions | 107 hours of sessions waiting on the owner; one denied `docker stop` sat 7.4 hours |
| Decides who may use the lab hosts and the scan target | one stuck scan job blocked two sessions |
| Allocates ports and version numbers | two sessions bumped the same `ver.py`; one dev server replaced another on the tunnel port |
| Splits work into streams, picks branches, keeps the ledger | children ran one after another for 28 hours in one 966k-token session |

What the dry run added about the hub itself:

- No task can be dispatched as written: 0 of 12 sampled. No task file has an `### Unattended run`
  section; 27 have no phase heading; one has `Files:` lines. Authority lives in parents' prose.
- The roadmap is stale (8 of 14 Now items are archived; no live parent is on it).
- The main hub checkout has 191 uncommitted entries from several sessions, one task's run state is
  split between two checkouts, and 96 worktrees exist, about 35 of them dead.

What the template already has, and this plan reuses without a copy:

| Existing | Used here as |
|---|---|
| Run-guard marker per session (task, repo root, pid, cwd, kind, transcript, mode) | the worker registry |
| Watchdog (`lib/run_watch.py`): `--idle`, restart caps | the stall timeout and the restart of a dead worker |
| Run state: `Decision:`, `Ruling:`, `Note: parked:` lines | the record of answers and parked questions |
| `at task report`, `at notify`, `agents-core:ask`, `agents-core:unattended-run` | the report, the notification, the question format, the authorisation section |
| `agents-tasks` skills (`add-task`, `triage-inbox`, `roadmap`, `audit-todos`, `complete-task`) | the task management a worker does when the supervisor asks |

What the harness already has (Claude Code 2.1.332): the agent view lists sessions with their state,
shows a waiting question, takes a reply, and is the only place a permission prompt can be answered.
This plan adds what it lacks and does not rebuild it.

## What the research says

1. Scheduling, claims, caps and locks live in code. OpenAI Symphony is a spec'd scheduler; Cursor's
   agent-held locks dropped 20 agents to the throughput of 1–3; Gas Town, with an LLM control loop,
   was abandoned by its author in August 2026.
2. The supervisor holds no state in its context; each wake starts from observed state on disk.
3. A worker's "done" is a claim. In a 203-person survey 41% often see a false "done".
4. One writer per unit of work, one worktree each.
5. Dispatch is not the measured bottleneck; review and validation are (Factory: orchestration 2.3%
   of mission time, validation 37%). One person ran 10–12 sessions with the agent view and no LLM
   between. So the LLM layer has to prove itself against that.
6. No controlled comparison of a human with a dashboard against an LLM supervisor exists, and no
   report of an LLM manager over `--bg` sessions running for days.
7. Text from a worker that reaches the supervisor is an injection path (arXiv 2510.17276). The
   supervisor acts on states and results written by code.
8. A message from another session can never approve a permission. Workers need their permissions
   before they start.
9. A session that lives for days is the costliest pattern the usage profile measured.
10. Anthropic's own coordinator (Claude Code Projects, beta) is cloud-only and does not fit local
    labs. The agent view is a research preview and changes often, so the parts built here must not
    depend on its details.

## Design

### Parts

| Part | What it is | Judgment |
|---|---|---|
| `at sup`, `at lease`, `at reserve` | stdlib code: packs, digest, leases, landing, readiness, queue | none |
| Watcher | one small detached process per profile; reacts to events | none |
| Workers | one session per task, in the task's own worktrees, running `agents-core:execute-plan` under `agents-core:unattended-run` | the task |
| Supervisor tick | a short fresh session the watcher starts when an event needs judgment | priorities, answers |
| Supervisor chat | the session the owner talks to | the owner dialogue |
| Agent view | native; the owner's window on workers and the place to approve a permission | none |

### State

Everything the supervisor knows is on the host, beside the run-guard directory, under
`${XDG_STATE_HOME:-~/.local/state}/agents-template/sup/<profile>/`:

| File | Content | Writer |
|---|---|---|
| `packs/<name>` | task IDs, order, branches, worktrees, PR state | `at sup pack` |
| `events.log` | worker stops, asks, resource requests, finishes; append-only, with a cursor file | hooks and `at sup` |
| `queue.md` | decisions for the owner, `agents-core:ask` format | `at sup queue` |
| `inbox/<TASK-ID>.md` | answers for a worker, each with an id | `at sup answer` |
| `instructions.md` | the owner's standing instructions, dated | `at sup instruct` |
| `board.md` | the last digest and what the supervisor decided on it | `at sup board` |
| `pid`, `watch.pid` | single-instance locks | `at sup start` |

Also there: `workers`, the registry of supervised session ids written by `at sup start-worker` (the
run-guard marker is writable by its own session, so it is not the authority), `touch.log`, one line
per owner action through `at sup`, and `kept/<TASK-ID>/`, files rescued from removed worktrees.

Every `at sup` command that changes state takes one `flock` for the profile. A question has an id
and is claimed by the first answer. The event cursor advances only when a tick exits 0.

Leases are host-wide, under `…/agents-template/leases/`. No checkout gets dirty from supervision.

### The supervisor is stateless (D6)

- A tick is a headless session with the supervisor agent, started by the watcher with a fixed prompt
  and the ids of the new events; no worker text is in the prompt. It has a time limit. It reads the
  digest, `instructions.md` and the board, acts through `at` commands, and ends. Events that arrive
  during a tick are batched into the next one. Expected load from the usage profile: 20–35 ticks a
  day (about 10 questions, 4–5 denials, plus lab requests). Each tick starts near the same small
  context, so there is no growth, no compaction and no cache to keep warm.
- The chat is the same agent, interactive, started by the owner with `at sup chat <profile>`. It
  holds nothing that is not in the files: the owner can clear or close it at any time and the next
  chat knows the same things. An instruction the owner gives is written at once with
  `at sup instruct`, and every tick reads it.
- The model is a profile field; the default is the strongest model available. Reading code,
  transcripts or diffs is delegated to a read-only `adviser` subagent that returns a short answer
  with paths.

### Events and the watcher

No hourly wake of an LLM. The watcher polls the event log and the registry every few seconds and
starts a tick only on an event. For supervised sessions the watcher owns liveness: it replaces the
per-worker watchdog (it reuses the checks of `lib/run_watch.py`), a worker in
`WAITING supervisor:` is not dead and is not restarted, and the watchdog's own owner notifications
are routed to the event log. In arm A, with no supervisor, every row that says "a tick" means: an
entry in the owner's queue and a notification.

Events are written by code:

| Event | Written by | The watcher does |
|---|---|---|
| Worker stopped: BLOCKED, GAVE_UP, EMPTY | the run guard, for a supervised marker | starts a tick |
| Worker finished a task (DONE) | the run guard | runs the done check; lands; starts the pack's next ready task when the profile allows, else a tick |
| `at sup ask` | the worker | starts a tick |
| `at sup need <resource>` | the worker | grants the lease when it is free and the resource is marked `auto`; else a tick |
| Lease released, overdue or owed | `at lease` | grants to the first waiter, or a tick |
| Worker dead or idle past `--idle` | the watchdog | restarts within its caps, then a tick |
| Tick failed or timed out | the watcher | notifies the owner |
| Queue got a blocking entry | `at sup queue` | notifies the owner |

A supervised stop does not notify the owner directly; the tick decides. With no live watcher the
hooks notify the owner as they do today. The watcher runs one tick at a time and passes each tick
the events since the cursor.

### Worker protocol

A worker learns it is supervised from the `supervised` line in its marker, written by
`at sup start-worker` (the `workers` registry, not the marker, is what the watcher trusts), and from one paragraph in `agents-core:unattended-run`:

- A question it may not decide: `at sup ask <TASK-ID>` with the question, options and its
  recommendation, plus the usual `Note: parked:` line. It continues with work that does not depend
  on the answer.
- A resource: `at sup need <resource> --minutes <n>`. If the lease is free the command returns with
  it. If not, the worker ends its turn on `Run: WAITING supervisor: <resource>`, a form the run
  guard accepts only for a supervised marker with an open request. When the lease is granted the
  watcher wakes the worker with a message, or resumes it.
- Answers: the worker reads `at sup inbox <TASK-ID>` when woken, at each phase start and before
  closeout, and records each entry as `Decision: [sup-<profile>] A<n>: <text>` or
  `Decision: [owner] A<n>: <text>`. The worker is the only writer of its `state.md`.

The supervisor reads a worker's structured fields (state, phase, the options of a question, check
results). Free text from a worker is passed to the adviser or quoted to the owner; it is never an
instruction to the supervisor.

### Tasks, worktrees and landing (D10)

- Every task runs in its own hub worktree on its own branch, created by `at sup start-worker`, which
  also creates or attaches the sibling worktrees the pack names and writes the worktree's
  `.local/repos.map`. Nobody works in the main hub checkout: it is the landing checkout and stays
  clean. The seed `AGENTS.md` and `agents-core:execute-plan` say that a supervised task's worktree
  is the right place to work, so the worker does not stop to ask about the branch.
- A task has one end state: closed out. The worker runs `agents-tasks:complete-task` when the
  phases and the final review pass, whatever the state of the sibling PRs. Waiting for the owner's
  merge is tracked on the pack, not on the task (D8): the pack stays open, the digest shows each
  sibling PR, and a change the owner or a PR review asks for after closeout is a new task in the
  same pack on the same sibling branch.
- The done check runs before closeout, while `_runs/<ID>/` still exists.
- `at sup land <TASK-ID>` takes a closed-out task. It squash-merges the hub branch into the default
  branch as one commit, under the `hub-ledger` lease, runs `at ledger sync` and `at ledger check`,
  and removes the hub worktree and branch. Workers in task worktrees do not run the ledger sync;
  only `land` does, so parallel tasks do not conflict on generated blocks. Landing happens when
  the task closes; a profile can set it to wait for the owner's word.
- Before the squash, the branch tip is kept as `refs/archive/task/<ID>`, so per-phase commits, run
  state and review evidence stay reachable and the SHAs named in the task log resolve. The default
  branch history gets one commit per task.
- `land` refuses to remove a worktree that holds ignored files other than caches; it moves them to
  `kept/<TASK-ID>/` first and prints the path.
- A dependent task starts from the default branch after its blocker landed, so `Blocked by`
  resolves as it does today.
- A task whose work is all in sibling repos still lands one hub commit: its task file.
- Landing is local. Pushing the hub is a separate step and the owner's.
- A conflict at landing: inside a generated ledger block, either side is taken and the ledger is
  rebuilt; in a hand-written file, landing stops with the files named, the worktree stays, and a
  new worker session for that task resolves it there.
- Sibling repos follow the profile, not this plan: the branch pattern (in RedMesh `feat/rm-NNN-<slug>`
  from `origin/develop`, one per repo per parent, picked by the owner), and whether streams of one
  parent get their own sibling worktrees.
- New IDs: `at reserve` sees only its own checkout, so two worktrees can take the same ID (this
  happened in RedMesh). It gets a host-wide high-water file per repo and prefix.

### Packs

A pack is a named set of task IDs with the sibling branches they share, in RedMesh a parent task and
its children. Its file records the order (`Blocked by` edges plus the parent's stated order), which
tasks may run at the same time, and the state of each sibling PR. A pack is open until its PRs
are merged or dropped. Sessions are capped per profile (default 3, because the trial host has 8
cores and 31 GiB with the lab already using 17).

Who starts what (D16): the watcher starts the next ready task inside a pack that is already
running. A pack starts on the owner's word, at any time and beside running packs, up to the session
cap: the owner says it in chat and the chat runs `at sup start-pack <name>`, or the owner runs it.
The owner can also pause a pack, reorder its tasks and change the cap the same way.

### Preparation (D9)

A task is dispatched only when `at sup ready <TASK-ID>` passes: integer phases, `Files:` fences,
named checks, acceptance criteria, an `### Unattended run` section with `Authorised`, `Owner only`
and `Defaults`, declared resources with durations, and a permission preflight: every command class
the task names is allowed in the worker's mode, because a headless worker's denial is silent.
Making a task ready is itself work the supervisor dispatches: a preparation worker edits the task file in its own hub worktree, collects
every open decision, and lands. The owner answers the collected decisions in one sitting; the
answers become `Defaults` lines. The digest shows, per pack, how many tasks are ready.

### Task management

"Full management of tasks" is done by workers running the existing `agents-tasks` skills on the
supervisor's request, each in a hub worktree that lands at once: triage of the inbox, new tasks,
roadmap refresh, the audit of stale tasks. The supervisor reads the roadmap horizons and the pack
files to choose what starts next, and proposes changes of priority to the owner through the queue.

### Leases

- `at lease take|release|list|clear|run`. Single holder. The file holds the holder's task, session
  id, pid with the process start time, reason, start and TTL, under `flock`.
- States: `held`; `overdue` (TTL passed, holder alive; still held, flagged); `owed` (holder gone and
  the resource needs a restore); free. `take` succeeds only on a free lease.
- A resource is declared in the profile with a restore flag and an `auto` flag (the watcher may
  grant it without a tick).
- A lease wraps a tool's own lock; it does not replace it. A downstream tool that already locks
  (in RedMesh `scan_run.py` takes `flock` and switches the target mode itself) keeps doing so.
- `full-suite` is a built-in resource; a heavy check is wrapped in `at lease run full-suite -- …`.

### D1 in code

- The supervisor agent is a file in the downstream `.claude/agents/`, written by `at sup init`,
  because a plugin-shipped agent ignores `permissionMode` and `hooks`.
- Tools are a positive list: Bash, Agent (adviser and the profile's operators only) and, in the
  chat, the question tool. No messaging tool, no Edit, Write, NotebookEdit, Read, Skill, MCP or cron.
- A PreToolUse hook checks every Bash command of a supervisor session without a shell: it splits
  the command with `shlex`, refuses any shell metacharacter, substitution, environment prefix or
  newline, and matches the argument list against exact tables: `at sup` subcommands,
  `at lease take|release|list`, `at run-guard status`, `claude agents`, and named read-only `git`
  and `gh` subcommands with a fixed set of flags (no `-c`, no `gh api`, no aliases). `at lease run`
  and `at lease clear` are not in the tables: `run` executes any command. Allow rules are not the
  enforcement.
- Chat only, never a tick: `at sup instruct`, `at sup answer --owner`, and the pack controls
  (`start-pack`, `pause-pack`, `order`, `cap`). `at sup chat`, run from the owner's shell, creates
  a token for that session; these commands require it, and a tick has
  none. Each recorded instruction is echoed to the owner, and the digest lists the instructions in
  force.
- Owner's shell only: `at sup push` and `at lease clear`. The chat prints the command; the owner
  runs it.
- Operators run named wrapper scripts from the downstream repo, one per operation; the hook of the
  operator agent allows those scripts and nothing else. No free-text commands.
- The supervisor runs with `bypassPermissions` (D12), so it never waits on a prompt. Two
  consequences. The hook and the tool list are then the only fence, so Phase 0 must show that a
  PreToolUse denial holds in that mode. And the harness holds messages between a bypass session and
  a session in another mode, so the supervisor does not message a worker directly: answers go
  through the inbox file and the watcher wakes the worker.
- Workers start only through `at sup start-worker`, which builds the prompt from the task file and
  says "this task only".

### The owner's interface

- Chat: "status" is the digest; the queue is shown first; every answer of the owner is recorded.
- Agent view: to watch a worker or approve a permission prompt, which no supervisor can do.
- Push: the owner runs `at sup push <pack>` in their own shell; the digest prints the line. It pushes
  the pack's sibling branches that pass the done check and carry the peer-review stamp where the
  repo requires it, and refuses protected branches itself, because a push inside a subprocess does
  not pass the git hook of the harness. No LLM pushes.
- End of a pack: after the merges, `at sup close <pack>` checks that every task is closed out and
  landed and every PR merged or dropped, starts a closeout worker for the parent task when the pack
  has one, and removes the pack's sibling worktrees.

### Done check

Before a task is reported done or landed, code checks: the run's final review passed; the commits
exist on the named branches; every repo in the task's Repos row has a branch with commits or a
recorded reason; the checks ran; downstream pins the task names are present. The digest shows the
result, not the worker's sentence.

### Digest

`at sup status` prints a bounded view: per pack the tasks, their state and readiness; per worker the
task, phase, state, time since last activity and context size where the harness gives it; leases and
waiters; the queue; branches ready to push with PR state; cost where the harness gives it.

## Facts to confirm first (Phase 0)

Known from the documentation and the installed CLI (2.1.332), so not facts to test: `--bg` starts in
the shell's directory and makes no worktree inside an existing one; project plugins load in
worktrees; `claude stop` keeps the conversation and the worktree; messages pass between `default`,
`auto`, `acceptEdits` and `dontAsk` sessions and are held when either side bypasses permissions;
`notify_when_idle` gives one notice; `CLAUDE_PID` and `CLAUDE_CODE_SESSION_ID` are set in Bash and
hook subprocesses; the main-session prompt cache is 5 minutes unless `promptCacheTtl` is set.

To observe:

| # | Fact | When it fails |
|---|---|---|
| 1 | A `--bg` session started by a detached process (the watcher) runs, and `claude agents --json` gives a usable state for it (field names differ between background and interactive rows) | workers are detached headless sessions; state from the marker and its `.status` |
| 2 | A `--bg` worker started inside an existing worktree does not push or open a draft PR when it finishes (since v2.1.198 it does in its own worktree) | workers are headless sessions |
| 3 | A stopped or idle worker can be woken by a process: a message, or `claude --resume <id> --bg "<text>"` | the worker is restarted as a fresh session for the same task; run state on disk carries it |
| 4 | The run guard and plugin hooks fire in a `--bg` session in a hub worktree, with `CLAUDE_PID` and the session id set | headless sessions, where this is already proven |
| 5 | A custom agent in `.claude/agents/` with a tool list and a `hooks` entry, started headless and interactive with `--agent`, runs that hook on every Bash call and has no other tool | the hook is installed in the profile's settings file passed by the launcher |
| 6 | A subagent of that session runs under its own hook, and cannot run a command its hook denies | operators are not subagents; the supervisor calls the wrapper scripts through `at sup op <name>` |
| 7 | A headless tick can use the Agent tool and finishes within a bounded time | the adviser runs as a second headless session |
| 8 | A worker that hits a permission denial or waits on a question can be told apart from a working one, from `claude agents --json` or the guard's `.status` | the watchdog's `--idle` is the only signal; the digest shows time since last activity |
| 9 | A headless session reports cost and context size (`total_cost_usd`); a `--bg` session exposes either | the digest shows them for ticks only |
| 10 | In a `bypassPermissions` session a PreToolUse hook denial still blocks the call, headless and interactive, and the agent's tool list still applies | the supervisor runs in `dontAsk` with the same hook |
| 11 | An `auto` mode worker, headless or `--bg`: what a classifier block looks like from outside, and whether the mode is available to a session a process starts | workers run in `acceptEdits` with an allow list from the profile and the preflight |

Record: `docs/meta/2026-11-26-supervisor-facts.md`, one entry per fact with the command, the observed
output and the version.

## Phases

Each phase lists files, a ceiling of new code lines (tests excluded) and checks. Tests are stdlib
`unittest` files under `scripts/tests/`, run by `run-all.sh`. Phases 1 and 2 need no harness fact.

#### Phase 0: Spike the harness facts

- Files: `docs/meta/2026-11-26-supervisor-facts.md`. No code.
- Checks: every fact has an observed output or "not available", and the plan is revised where a
  fallback applies.

#### Phase 1: Leases and safe IDs

- Files: `plugins/agents-core/lib/lease.py`, `lib/at.py` (wiring), `scripts/tests/test_lease.py`,
  `plugins/agents-tasks/skills/task-ledger/scripts/reserve_work_item.sh` and its test. Ceiling: 300.
- Checks: two processes race for one lease and one wins; a dead holder frees a plain lease and gives
  `owed` on a restore one; a reused pid with another start time counts as dead; TTL expiry with a
  live holder gives `overdue` and `take` fails; `run` releases on a failing command; two checkouts
  of one repo reserve different IDs; with no writable state directory `at reserve` behaves as today.
- Useful alone: any two sessions can share a resource; the ID collision is gone.

#### Phase 2: A hub worktree per task, landing, readiness

- Files: `plugins/agents-core/lib/sup.py` (`worktree`, `land`, `ready`), `lib/at.py` (wiring),
  `scripts/tests/test_sup_land.py`, a paragraph in `agents-core:git-discipline` and in the seed
  `AGENTS.md`. Ceiling: 350.
- Checks: `land` gives one commit on the default branch and removes the worktree; it refuses a dirty
  landing checkout and a task that is not closed out; a generated-block conflict is rebuilt; a
  hand-written conflict stops it with the files named; a dependent task started after the landing
  sees its blocker done; the pre-squash tip is reachable from `refs/archive/task/<ID>`; ignored
  files are moved, not deleted; `ready` fails on each missing item with its name.
- Useful alone: the owner's sessions stop sharing one checkout, and the default branch gets one
  commit per task.

#### Phase 3: Packs, digest, worker protocol, watcher. Trial arm A

- Files: `lib/sup.py` (`pack`, `status`, `start-worker`, `stop-worker`, `ask`, `need`, `queue`, the
  done check), `lib/sup_watch.py`, `lib/run_watch.py` (supervised sessions), `hooks/run-guard.sh`
  (events, the `WAITING supervisor:` form), `lib/at.py` (`run-guard status --all`), tests for each,
  the paragraph in `agents-core:unattended-run`, one line in `agents-core:execute-plan`. Ceiling:
  1,500 (the one-session watchdog alone is 540 lines). In arm A the owner answers a worker in the
  agent view and `ask` writes to the queue, so `answer`, `inbox`, `board`, `close` and `push` move
  to Phase 4. Also here: `start-pack`, `pause-pack`, `order`, `cap`, and `measure`.
- Checks: the digest from fixtures; the watcher starts the next ready task on DONE and grants a free
  `auto` lease; a waiting worker's stop is accepted by the guard and refused without an open
  request; a waiting worker is not restarted; `start-worker` refuses above the cap, on a task
  that is not ready, and for a second live worker on one task; a second watcher is refused; with no
  live watcher the guard notifies the owner.
- Trial arm A, no LLM supervisor: the owner manages two prepared packs with `at sup status`, the
  queue, the watcher and the agent view. Measured with `at sup measure`: owner touches per event,
  time from an event to the worker's next step, cost, wrong "done" claims.
- Useful alone: this is already the owner's dashboard and scheduler.

#### Phase 4: The supervisor. Trial arm B

- Files: the agent template and `at sup init|chat`, the D1 hook
  (`plugins/agents-core/hooks/sup-guard.sh`) and its tests, the tick launcher in `lib/sup_watch.py`,
  `plugins/agents-tasks/skills/supervise/SKILL.md` (≤ 200 lines), the adviser agent, seed
  `.config/supervisors.project.md`, and `answer`, `inbox`, `board`, `close`, `push` in `lib/sup.py`.
  Ceiling: 700.
- Checks: the hook denies each forbidden command class from a list of cases, including compound
  commands, redirections, substitutions, environment prefixes, `git -c`, `gh api`, `sh -c`,
  `at lease run` and absolute paths; a tick cannot run a chat-only command; an unread inbox entry
  blocks closeout; two answers to one question give one winner; a tick
  reads `instructions.md`; a forced kill of a tick leaves no half-written state.
- Trial arm B: the same kind of two packs with the supervisor. Same measures, plus supervisor cost
  and the share of worker questions it answered.

#### Phase 5: Decide the rest from the trial

Each as its own task, only on evidence: a second profile on one host; Codex workers; counted leases
and blackout windows; a checker for the profile file; a `Parent` row in the task format; release.

## Before the trial, in the RedMesh hub (D9)

Downstream work, not this repo, done after the release that carries Phases 1 and 2. Cleaning the
main checkout needs the owner.

- One resource policy, decided (D13): the supervisor's operators control rm1, rm2, the canary and
  the target under leases, with standing approval. The hub documents that disagree (RM-268, RM-276,
  `scan-target.md`) are rewritten to say so, with the restore step of each resource.
- The main hub checkout is committed or cleaned (191 entries), and the split run state is reconciled.
- The hub's `AGENTS.md` rule "work on the default branch" gets the exception for task worktrees.
- About 35 dead worktrees are pruned; the roadmap's Now and Next are rebuilt.
- The profile `redmesh`: every area (RM, RMP, RMM, EG, EGM); resources `lab`, `canary`, `target-mode`,
  `tunnel-35543`, `edge-node-ver`, `full-suite`; the branch pattern.
- The hub rule "children stay open until the owner's merge" (RM-268 D41) is replaced by: a child
  closes when its work is done, and the parent closes after the merges.
- The lab operations become wrapper scripts; `scan_run.py monitor` runs detached; the lab binding
  file is reachable from a task worktree.
- Two packs are prepared. Candidates from the dry run: RM-152 (edge only, no lab) and RM-275 (edge
  only, lab). RM-276 stays out; a live session holds it.

## Order

Four items of the usage profile come first, as their own task, because every worker runs
`agents-core:execute-plan` and the waste multiplies per worker: the test-scope ladder (A1), the
long-command rule (A2), the permission preflight (B10) and the peer stamp keyed on the patch (B12).
The review loop cost (the profile's conclusion 3) and the load of subagents, which the session cap
does not count, stay open and are watched in the trial. Then Phase 0, then 1 and 2 in parallel
with the hub preparation, then 3, 4, 5.

The code is built and released from this repo, and the hub gets it by plugin update; nothing is
prototyped in the hub first, so no second copy has to be carried back. Each phase that is useful
alone ships in its own release.

## Acceptance

Both arms run two prepared packs of at least two tasks each, one pack with a lab step.

Arm A (Phase 3):

- No two sessions wrote in one checkout, and the hub's default branch got one commit per task.
- Two workers that needed the lab used it one after the other, and it was restored after each.
- A stopped or waiting worker reached the owner's queue or its next step within 5 minutes.
- No task was shown as done that failed the done check.

Arm B (Phase 4), against arm A:

- Per event (a worker's stop, question or resource request): owner touches, counted from
  `touch.log` and the agent view replies the owner notes, are at least 30% lower, and the median
  time from the event to the worker's next step is not higher.
- Supervisor cost in USD is under 15% of worker cost, from the headless cost reports; where a worker
  gives none, the supervisor's cost is reported alone.
- Every answer the supervisor gave is a `Decision: [sup-…]` line, and the owner, reading them all
  after the run, overrules at most one in ten.
- No tick ran a denied command class; the hook log shows every denial.
- A killed tick and a cleared chat lose nothing: board, queue, packs and instructions are unchanged.

How the two numbers are computed, by one script (`at sup measure`, Phase 3) over a trial's
transcripts and state, the method the usage profile used: an event is a line in `events.log`; an
owner touch is a message the owner typed in any session of the trial or a line in `touch.log`; the
time to the next step is from the event to the worker's next tool call; cost is the reported USD of
each session, or tokens at list price where none is reported.

Stop rule: when arm B misses the first two lines, the supervisor is not built further and arm A is
the product. The 30% and 15% are placeholders: arm A gives the baseline, and the owner sets the
thresholds after arm A and before arm B. Limits of the comparison: four tasks, different packs,
arm B second, and one lab slot that dominates elapsed time; so the rule uses per-event measures, the owner's time to read the
supervisor's decisions counts as owner touches, and a second round swaps the packs between arms.

## Out of scope

- A hosted service, a web board, workers on other machines, Claude Code Projects.
- Automatic merge or release; pushing without the owner's word.
- A second lab slot in RedMesh.
- Agent teams.

## Risks

- The agent view and background sessions are a research preview. Phases 1 and 2 use none of it, and
  every Phase 0 fact has a headless fallback.
- The vendor may ship a local coordinator. The code layer (leases, landing, readiness, digest) keeps
  its value under any coordinator.
- A model change can break supervisor behaviour, as happened to Gas Town. Ticks are short and the
  trial is repeated at each model change.
- One lab slot serialises most RedMesh work whatever the supervisor does.
- Preparation is the larger effort. If tasks cannot be made ready cheaply, no supervisor helps.

## Decisions (owner, 2026-11-26)

- D1: the supervisor writes no code; it monitors and supervises other sessions.
- D2: it starts and stops worker sessions itself.
- D3: it shares lab resources between workers; an operator under the supervisor works the lab, and
  workers notify the supervisor when they need it.
- D4: it answers worker questions inside the recorded authorisation; tasks are prepared well first.
- D5: supervisors are profiles defined per downstream repo; several can run from one hub.
- D6: the supervisor is stateless: a chat the owner can clear, and fresh sessions per event.
- D7: the trial is staged, with an arm without the LLM supervisor first.
- D8: the owner picks the `feat/rm-NNN` branches and parallel streams are allowed inside a parent.
  Amended the same day: a child task closes when its work is done; the supervisor tracks the merge
  on the pack, and the parent closes after it.
- D9: preparation and hub hygiene come before any trial.
- D10: every task works in its own hub worktree and is merged locally into the default branch,
  squashed, when it is done or when the owner asks.
- D11: workers run in `auto` permission mode.
- D12: the supervisor runs with `bypassPermissions`. Its limits come from the D1 hook and its tool
  list, not from prompts.
- D13: in RedMesh the supervisor controls the whole lab (rm1, rm2, the canary, the target) through
  its operator agents, with standing approval; no owner go per scan round.
- D14: RedMesh starts with one profile, `redmesh`, covering every area including EG and EGM. The
  profile mechanism stays so that a split is possible later.
- D15: preparation covers the packs chosen for work, not all active tasks.

- D16: a closed task lands automatically. The watcher starts the next ready task inside a running
  pack; a pack starts on the owner's word, also beside running packs. The supervisor answers a
  worker only inside the task's `Authorised` and `Defaults` lines and the owner's standing
  instructions, never above the repo's `Autonomy max`.
- D17: the code is built and released in the template repo first; downstream repos get it by update.

## Open questions

- Whether `git worktree remove` deletes ignored files without refusing (to verify in Phase 0).
- Which plugin holds the `supervise` skill; `agents-core` stays small, `agents-tasks` owns tasks.

## History

Version 1 (2026-11-26): one long-lived supervisor session with a timer wake, packs as one hub branch
with one worker at a time. Four rounds with `agents-core:plan-critic` (REVISE, REVISE, REVISE,
PROCEED at composite 3.6) checked it against the template's code. A second research round then
found: eleven statements the Claude Code documentation contradicts (among them that `dontAsk` does
not bound Bash, that no per-subagent Bash allow-list exists, that plugin agents ignore
`permissionMode` and `hooks`, and that the prompt cache is 5 minutes); no worker-side protocol; a
timer wake slower than the owner is today; a days-long session as the measured anti-pattern; no
endgame; and a pack model that would have made RM-268's 25 tasks serial and broken four of the hub's
rules. Version 2 is the reshape. Version 1 was never committed.
