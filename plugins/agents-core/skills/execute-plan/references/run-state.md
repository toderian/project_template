# Run state: `docs/tasks_manager/_runs/<TASK-ID>/`

The run directory is the orchestrator's memory. It is committed with each phase commit (except
`diff.patch`, which the seed `.gitignore` block ignores because it is regenerable), so any session on
any machine can resume. `agents-tasks:complete-task` copies its `Ruling:` lines into the completion
summary and removes the directory.

## Layout

```text
docs/tasks_manager/_runs/<TASK-ID>/
  state.md                 resume map; rewritten by the orchestrator only; keep under 60 lines
  lock                     `<pid> <host> <started>` while `at task run` (or an orchestrator that
                           chooses to) holds the run; git-ignored
  phase-N/brief.md         at task brief <TASK-ID> --phase N, plus the orchestrator notes you append
  phase-N/report.md        implementer's full report (its chat reply is ≤ 15 lines)
  phase-N/diff.patch       git diff <BASE> -- <scope fence>; the reviewers' input (git-ignored)
  phase-N/size.md          at task size <TASK-ID> --phase N: lines per file before/after, code/test/docs split,
                           Flagged:. Size files are committed with the run directory (evidence; diff.patch is not)
  phase-N/size-fix-R.md    at task size <TASK-ID> --phase N --fix R: what fix round R alone changed
  phase-N/review.md        small mode: the single reviewer's reply, Stage: both (you save it)
  phase-N/review-spec.md   large mode: reviewer reply, Stage: spec (reviewers are read-only: you save the reply)
  phase-N/review-quality.md large mode: reviewer reply, Stage: quality
  phase-N/review-security.md security-auditor reply, only when the phase touched a security surface
  phase-N/findings-R.md    numbered open findings handed to fix round R
  phase-N/re-review-R-<stage>.md scoped re-review reply after fix round R
  validation.md            optional spec-validator run over all acceptance criteria (step 6)
  size.md                  at task size <TASK-ID> --final: the whole run's size, the PR-size input
  final-review-1.md, -2.md the whole-task reviews (step 7; only -1 in small mode); final-findings.md if a fix wave ran
  final-review-simplicity.md the Stage: simplicity review (large mode)
  architecture-review-peer.md, final-review-peer.md, verify-peer.md
                           replies saved by `at peer run` (the other agent CLI), only where the
                           checkout enabled peer checks; the outcome is a `Note: peer ...` line in state.md.
                           `final-review-peer.md` is mandatory when the code checkout is `required`
```

## `state.md` format

Written by `at task run-state init`, validated by `at task run-state check`, edited by hand between:

```markdown
---
task: EGM-012
task_file: docs/tasks_manager/_todos/EGM-012-F_example.md
runtime: claude | codex | inline
mode: small | large
mode_reason: 3 phases
base_rev: a1b2c3d
branch: master
work_mode: default-branch | same-branch | task-branch | read-only | ask
autonomy: L0 | L1 | L2 | L3
code_repo: ../edge_node         # optional: checkout holding the code diff; default: this checkout
current_phase: 2
updated: 2026-09-15T14:02:00
---
# Run ledger — EGM-012

| Phase | Status | Attempt | Spec | Quality | Security | Open | Commit | Agent |
|---|---|---|---|---|---|---|---|---|
| 1 | committed | 1 | PASS | PASS | n/a | 0 | 9f8e7d6 | — |
| 2 | fixing | 2 | FAIL | PASS | PASS | 1 | — | agent-3f1c |

Phase 1: BASE a1b2c3d; complete (commit 9f8e7d6, review clean)
Phase 2: BASE 9f8e7d6; fix round 1/3 (2 addressed, 1 open: validator ignores empty payload)
Ruling: empty-payload check — accepted as-is, phase 3 owns payload validation — cost if wrong: one extra 400 path
Decision: stuck job blocks the baseline scan — hard-stopped it — why: inside the authorised lab scope — cost if wrong: one lost partial scan
Interface: SessionValidator.validate(token) -> Result[Session, SessionError]  (phase 1, for later phases)
Note: e2e is N/A for this repo (no browser harness); recorded in the task file
```

Rules the validator enforces:

- Frontmatter keys: `task`, `task_file`, `runtime`, `base_rev`, `branch`, `work_mode`, `autonomy`,
  `current_phase`, `updated`. `runtime` is `claude`, `codex` or `inline`. `mode` (`small` | `large`)
  and `mode_reason` are written by the orchestrator; a file without them is a large run.
- `code_repo` (optional, path relative to this checkout or absolute) names the checkout that holds the
  code diff when it is not the one holding `_runs/`. `at task run-state check <TASK-ID> --final` (run at
  the end, before closeout) fails when a row is `committed`, `final-review-peer.md` is missing and
  `git config agents.peerRequired` is true in that checkout. Without `--final` the check never asks for it.
- One table row per `#### Phase` heading in the task file, numbered like the ledger's `n/m`.
- `Status` is one of `pending | implementing | reviewing | fixing | committed | blocked | parked`.
- `Spec`, `Quality`, `Security` cells are `—` (not run yet), `n/a`, `PASS` or `FAIL`. In small mode the
  single reviewer's verdict fills both `Spec` and `Quality`.
- A `committed` row has a SHA in `Commit`, and every SHA must exist in the repository.
- Free lines after the table start with `Phase N:`, `Ruling:`, `Decision:`, `Interface:` or `Note:`.
  Nothing else. `Ruling:` closes a review finding; `Decision:` records a choice you made where you
  would otherwise have asked the owner (`<question> — <chosen> — why: … — cost if wrong: …`).
- `Agent` holds a subagent id when the runtime can resume by id (Claude Code); otherwise `—`.
  The scripted driver writes `waits` there for a row it parked only because a dependency is not
  committed: such a row reruns by itself once the dependency commits; clear the cell and it needs
  `--retry-blocked` like a row parked for its own reason.

`Open` is the count of findings not yet fixed or ruled. `Attempt` counts implementer dispatches for
the phase including fix rounds.

## Run guard

`at run-guard arm <TASK-ID|state.md>...` writes a marker for this session outside the repo
(`~/.local/state/agents-template/run-guard/<session id>`): the targets, plus `meta` lines (`pid`,
`cwd`, `armed`). While a guarded task is still in `_todos/`, or a guarded `state.md` has a row that is
not `committed`, the plugin's Stop hook (`run-guard.sh`) ends a turn only on a `Run: WAITING …` or
`Run: BLOCKED …` line. It never touches another session and lets the stop through after five
sent-backs in a row, or when all that is left open is a state file that no longer exists
(`kind=GAVE_UP`). At every stop it lets through it writes `<session id>.status` (`last_stop`,
`kind` = WAITING, BLOCKED, GAVE_UP, EMPTY or DONE, `text`, `transcript`, `mode`); when nothing is open
it writes `kind=DONE` and the marker is inactive until a new `arm`. After a compaction or a resume,
the `run-guard-remind.sh` SessionStart hook prints the open tasks and the first open row, so the run
is picked up from `state.md`. `at run-guard status` shows the targets and the status; `at run-guard
disarm` removes all of the session's files, and so does the 14-day prune. When it lets a stop through
as `BLOCKED`, `GAVE_UP`, `EMPTY` or `DONE`, the hook also runs `at notify` (detached, so it never
delays or changes the stop), which calls the owner's `agents.notifyCommand` / `AGENTS_NOTIFY_CMD`:
a program run without a shell, the title as its last argument, body on stdin, once per event (`<session id>.sent/<key>`).

`at run-guard arm --watch [--allow-bypass] [--budget-usd 4] [--max-resumes 4] [--interval 600]
[--idle 90] [--until HH:MM] <targets>` also starts a detached watchdog (`at run-guard watch`, one per
session: `<session id>.watch` holds its pid, `<session id>.watch.log` its capped log; the marker gets a
`meta watch` line). What the watchdog must remember is one record, `<session id>.watch.state`: the
restart caps of the first `arm --watch` (`--max-resumes`, `--budget-usd`, `--allow-bypass`), the restarts
used, the pid of a running restart, the last permission mode seen, and the events already sent.
`--until`, `--idle`, `--interval` and `--pause` belong to each watcher alone. Any re-arm keeps a live
watcher and its caps as they are; `arm --watch` with a dead one starts a watcher that continues from the
record, and its flags can only lower the recorded caps (`--allow-bypass` is never added later; a merge
that leaves less than 0.01 USD per restart refuses to start). `arm --watch` prints the restarts left, and
warns at zero that the watcher only reports. To change the caps or start a new count: `at run-guard
disarm`, then `arm --watch`. Only `disarm` and "finished" remove the record; a record that cannot be
read or is out of range counts as damaged and leaves no restarts.

Each tick it reads the marker and `.status`. "Finished" needs evidence: the marker holds a target and
every target could be read; then `DONE` or nothing open notifies "finished" (the hook's event key, so
the owner gets one message), runs `at task report`, and exits. An unreadable target is looked at again,
and notified as "idle" after the idle limit. `BLOCKED`: it notifies and never restarts. A live session
(the `meta pid` is a running claude process), or a restart still running, is never restarted: after
`GAVE_UP`, `EMPTY` or `--idle` minutes without a target change it notifies "idle" once, and the
in-session heartbeat owns the waking. A dead session with work open is restarted with `claude --resume
<id> -p "<fixed prompt>"` in the marker's `cwd`, after a pause that doubles each time, at most
`--max-resumes` times in all, each with `--max-budget-usd` = budget / max-resumes (floored to cents);
then it notifies "gave up" and exits. Before every restart it re-reads each open task file: the
`Execution` cell must hold `unattended` and every `Watch:` line of its `### Unattended run` section
must say `on` (at least one, and no other value); a marker
without a task is never restarted. The permission mode is the one in `.status`, else the last one
recorded, else `default`, and must be `default`, `acceptEdits` or `plan`; `bypassPermissions` needs
both `--allow-bypass` on the first arm and an `allow bypass` line in every open task's section.
Anything refused is notified (`refused-<reason>`) and ends the watcher, as do `--until` and `disarm`.
The watcher's own events (idle, restarted, gave up, refused) are sent without an event key, so
nothing in `.sent/` can silence them. Idle and restarted are deduped by the record; gave up and
refused end the watcher and are never deduped, so each watcher that ends for that reason says so.

Limits. Liveness is the recorded `meta pid` (and the restart the watcher started): an owner who
resumes a dead session by hand should `at run-guard disarm` first, or the watchdog may restart it a
second time. The caps guard against a run that loops by accident, not against a session that sets out
to defeat them: the watched session can run `at run-guard disarm` and then `arm --watch` with new caps,
and it can start `claude` itself. This is accepted; nothing here defends against it.

## Resume

A resumed run starts from the file, not from memory:

1. Read `state.md`. Run `at task run-state check <TASK-ID>`; fix the file before continuing if it fails.
2. For every `committed` row, confirm the SHA with `git cat-file -e <sha>^{commit}` and that the phase
   checkboxes in the task file are ticked. A missing commit means the branch moved: stop and ask.
3. Re-read every `Ruling:` and `Interface:` line; they go into the next brief's orchestrator notes.
4. If `lock` exists and names a live process on this host, another run is in progress: stop.
   A dead pid is a stale lock from an aborted run; delete it and continue.
5. `git status --short`. Uncommitted changes inside a phase's scope fence mean an implementer was
   interrupted: package them as `diff.patch` and go straight to review for that phase, or discard them
   only with the user's consent.
6. Continue at the first row that is not `committed`:
   - `pending` → step 5 from the brief.
   - `implementing` → the brief exists; dispatch a fresh implementer (a stale `Agent` id from another
     session cannot be resumed; leave it and continue).
   - `reviewing` / `fixing` → regenerate `diff.patch` from `BASE` and rerun the reviews or the pending
     fix round; the `findings-R.md` files say where the loop stopped.
   - `blocked` / `parked` → a human decision is recorded as missing; ask before continuing.
7. Arm the run guard again: the marker belongs to the session that wrote it.
8. Set `runtime:` to the runtime you detected now — it may differ from the session that started the run.

## Without agents-tasks

For `docs/_plans/<slug>.md` or a pasted plan in a repo without the task ledger, keep the same loop
with the run directory at `docs/_plans/_runs/<slug>/` and write the files by hand:

- `brief.md`: the phase heading and body, the plan's acceptance criteria and checks, the same
  `## Orchestrator notes` and `## Report contract` sections `at task brief` would emit.
- `state.md`: the format above, `task_file` pointing at the plan.
- Phase numbering follows the plan's `## Phase N:` / `#### Phase N:` headings in order.

`at ledger check` does not know this directory; remove it by hand when the plan is done.

## Scripted driver

`at task run <TASK-ID>... [--harness claude|codex] [--mode small|large|auto] [--phase N] [--check CMD]... [--security]
[--model M] [--strong-model M] [--effort E] [--strong-effort E] [--max-rounds 3] [--timeout 1800] [--budget-usd 5] [--no-commit]
[--no-final-review] [--lanes N] [--retry-blocked] [--at-review-cap park|continue] [--force-unlock] [--dry-run]` executes this loop without an orchestrating session: it writes the same files, one
process per dispatch, and commits each phase (`feat: <ID> phase N — <title>`), leaving `state.md`
dirty until the next phase's commit sweeps it in and committing the last one as
`chore: <ID> run state`. Differences from the skill:

- `--mode auto` (default) picks large on ≥ 3 phases, `--security`, a `Repos` row naming more than one repo, a `### Design`
  section or `Execution: orchestrated`; it cannot count files. Small mode still dispatches an
  implementer (the driver has no "self") but runs one `Stage: both` reviewer per phase and one
  final reviewer (none for a single phase), short of the skill's two reviewers per round; add the
  second reviewer and the peer by hand. A run never de-escalates from large.
- Final reviewer 2 gets the same prompt as reviewer 1 (anchored); the unanchored brief is the skill's.
- The clean-tree gate is strict: any change outside `_runs/` stops the run.
- The scope fence is "only what the phase requires"; the script cannot infer file lists.
- Security review runs on every phase or none (`--security`); checks come from `--check`, and on
  Claude the reviewers may run exactly those commands (`Bash(<cmd>)` allow rules) and nothing else.
- At the fix-loop cap the row becomes `blocked` with the open findings noted; there is no
  adjudication. Add `Ruling:` lines (or fix by hand) and rerun — with `--retry-blocked` if you leave
  the row `blocked`, or plainly after setting it back to `pending`. In an `Execution: unattended` task
  (a comma-separated cell: `orchestrated, unattended` counts, `not unattended` does not) pass
  `--at-review-cap continue` (default `park`; in a chain it applies to every task). The flag is the only
  source of this rule: the task file is writable by the implementers the driver dispatches, so the
  driver reads nothing about it from there. `continue` commits only
  when the loop really reached the cap and every open review is a `FAIL` whose header reads exactly
  `## Findings: N (C:x I:y M:z)` with x+y+z = N = the numbered findings parsed, no critical anywhere;
  any doubt parks, so a reply without a counted header (the security auditor's today) always parks. The
  `Decision:` line in `state.md` and the commit message name each open finding by severity, stage and
  review file, never by its text. A fix round whose implementer returns `BLOCKED`, `NEEDS_CONTEXT`
  or no status blocks the row and commits nothing.
- `After:` lines (`agents-tasks:task-ledger`, todo-convention) order the phases: a phase runs once
  every phase it names is committed, a phase without the line waits for the previous one. An `After:`
  naming a phase that does not exist, or a cycle, is an error before any phase runs (exit `2`). A row
  that ends `blocked`, including after a dispatch timeout or failure, no longer stops the run: its
  edits go to `git stash` (`at task run: <ID> phase N not finished`, named in the row's `Note:`; a
  failing `git stash` aborts the run), the phases that do not depend on it still run, and its
  dependants are set `parked` with a `Note:`. With `Execution: unattended` the failed row itself is
  `parked` too, since nobody answers a `blocked` one. A rerun skips `blocked` rows and rows parked for
  their own reason unless `--retry-blocked`; a row the driver parked only because of a dependency is
  re-evaluated and runs once that dependency is committed. A baseline-check failure, a commit failure
  and a failed post-phase check still abort the run (exit `1`), and so does an implementer that
  commits: the driver compares `HEAD` with the phase base after every implementer dispatch. `--phase N` ignores `After:`.
- What is committed is what was reviewed: when a review's diff is packaged the driver stages the phase's work and
  records its tree (`git write-tree`); just before the commit it takes the tree again, and a different one (a file
  written after the review, also by a check) blocks the row with `the tree changed after review (<paths>)` instead
  of committing. The commit adds only the driver's own paths on top: the run directory, the task file and the
  ledgers `at ledger sync` writes; a failed commit, the run-state one included, aborts the run (exit `1`). Every
  git process the driver starts runs with `GIT_NO_REPLACE_OBJECTS=1`, so a replace ref cannot show reviewers other
  content than the commit stores. SIGINT and SIGTERM terminate every running harness (each runs in its own
  process group), release the lock and exit `130` and `143`.
- Lanes: `--lanes N` (1-3, default 1; not with `--no-commit`) runs phases at the same time. A phase states its
  scope fence in `Files:` lines under its heading (comma-separated repo-relative paths, no glob, no `..`; several
  lines add up; no convention names one elsewhere). A wave is the ready phases whose fences do not overlap, lowest
  first, at most N; a phase without a valid `Files:` line never shares a wave, and a wave of one runs the ordinary
  serial loop. `--dry-run` prints the planned waves. Each lane is a worktree beside the repository
  (`<repo>-lane-<ID>-p<N>`) on branch `at-lane/<ID>-p<N>`, run by its own `Runner` through the same phase loop, one
  process tree per lane. A lane commits its reviewed tree only, never the task file or run directory, and only on
  its own branch (`HEAD` must be `refs/heads/at-lane/<ID>-p<N>`); its `state.md` is a private copy. An implementer
  commit in a lane blocks that lane like any implementer commit. Only the driver thread, under the run lock,
  writes `state.md`, the task file and the integration branch.
- A wave is one transaction on the integration branch. The driver commits the run state, then saves `Note: wave K:
  base <sha>, phases a, b` before the first merge. Lanes merge lowest phase first by the full SHA the lane's
  `Runner` committed (`git merge --no-ff`; that commit's tree must be the one its last review saw and its only
  parent the base, so a commit put in its place can differ in its message only), then every `--check` runs. A refused merge (`merge refused: <git's last line>`), a conflict (`git merge
  --abort`, never resolved) or a red check puts the integration branch back to the SHA before that merge (files a
  check created are removed with it) and parks
  the lane (`blocked` when the task is not `unattended`), worktree kept; the rest go on. One `Stage: both` review of
  `base..HEAD` (`wave-<K>/review.md`) follows; its prompt names each phase's fence and the paths a lane changed
  outside it. A failing review, or anything dirty in the integration checkout outside the driver's own files (an
  implementer that wrote outside its lane; those paths are named, edits to tracked files are saved to
  `wave-<K>/stray.patch`, untracked ones are left in place), undoes the whole wave: the
  branch goes back to the base, every merged lane is parked or blocked with its worktree and branch kept, and
  `Note: wave K: undone — <why>` says so. On a pass the driver ticks the task file, syncs the ledgers, sets the rows
  `committed`, notes `Note: wave K: done` and makes one bookkeeping commit (`chore: <ID> wave K`) of its own paths,
  then removes the merged lanes. If that commit fails (a pre-commit hook), `state.md` returns to its text before
  the done lines, nothing stays staged, the run exits `1` and the wave stays open for the recovery below. A wave
  that merged nothing uses no wave number. "Back to a SHA" means `git reset`
  to a SHA the driver recorded, with the files outside the run directory restored; the run directory is the
  driver's record and is saved from memory.
- Recovery after a kill, at the start of every run (with or without `--lanes`, also `--phase N`): a `Note: wave K:
  base <sha>` without its `done` or `undone` line stops the run with exit `1` before any dispatch and prints the
  recovery: `git reset --hard <sha>` (the base holds the run state as it was before the wave), then rerun; the
  driver resets nothing itself. Then every lane worktree and `at-lane/<ID>-p*` branch of the task is looked at: one
  that is clean and holds no commit of its own (its tip is on the integration branch's first-parent line) is
  removed and its phase runs as usual, and so is a clean one whose row is `committed` and whose tip is an ancestor
  of `HEAD` (a run killed before it removed its merged lanes); one that holds work (uncommitted changes, an unmerged commit, or a merged
  lane commit) is reported, its row is parked with a `Note:`, nothing is deleted, and that phase is not run,
  serially or in a lane, so a phase is never implemented twice. Merge or remove it by hand and set the row to
  `pending`. Harnesses of a run killed with SIGKILL may still write in their worktree; a rerun only removes clean,
  empty ones.
- Chain: `at task run <ID> <ID>...` first checks every id (`[A-Z][A-Z0-9]*-<n>` with a task file; else
  exit `2`, nothing runs), then runs the tasks in the order given and skips one whose `Blocked by` task
  is not `done`. A task this chain ran counts as done only when all its rows are committed (not after
  `--phase N` or `--no-commit`).
- Exit codes: `0` every row of every task committed and the final review passed, except that
  `--phase N` and `--no-commit` also exit `0` with rows not committed; `1` a row is `blocked` (a dispatch failure or timeout is `4` in an unattended run, where the row
  is parked, and `1` otherwise), the lock is held, the state is invalid, a post-phase check or the
  final review failed; `2` bad arguments, an invalid task id or `After:` graph, or no harness on
  `PATH`; `4` the run finished with `parked` rows or a skipped chain task and no `blocked` one. `1`
  wins over `4`.
- `--model` / `--effort` apply to implementers; `--strong-model` / `--strong-effort` to reviewers,
  final reviews and the fix round after two failed ones (each defaults to its routine value, and
  that to the harness default). Effort is passed as the harness names it. The execution-log
  headings record what was set: `(at task run, claude, model sonnet/opus, effort medium/high)`.
- `driver.log` in the run directory records every process, its stderr and (Claude) its cost.
- Every dispatch is bounded: `--timeout` kills a silent process and marks the row `blocked`;
  `--budget-usd` is passed to `claude -p` as `--max-budget-usd` (Codex has no equivalent — the
  timeout is the only cap there). A reply without a status block is asked for once more, like the
  `SubagentStop` hook does for subagents, then the row is `blocked`.
- One run at a time: the `lock` file refuses a second driver while the first is alive.
- After each commit it runs `at task run-state check` and `at ledger check`; a failure blocks the next phase.

## Morning report

`at task report <TASK-ID>... [--since <rev>]` writes `docs/tasks_manager/_reports/<date>-<TASK-ID>.md`
(`<date>` = commit date of `base_rev`), a function of the run's ledger: the commits recorded in the
phase rows, in row order, not of HEAD, so a rerun is byte-identical. Commit it with the run. "Needs
you" is what is open now: `parked` and `blocked` rows with their ledger lines, and `Note: parked`
lines (`Note: parked: <question>` and the driver's `Note: parked phase N: ...`) while a row is not
`committed`; afterwards they sit under "Parked during the run". `--since <rev>` adds the commits
`rev..HEAD`. A task with no run state is read from its archived `## Completion summary` (dated by its
`Base:` line or `--since`); one with neither is an error. `at ledger check` accepts `_reports/`.
