# Unattended run hardening: plan

Date: 2026-11-26. Status: decisions D1–D4 made by the owner on 2026-11-26; not started.

## Goal

A run started with `agents-core:execute-plan` on a task marked `Execution: unattended` reaches its
end, or a real owner decision, without a person watching. The owner learns within minutes when it
needs them, and reads one file in the morning to see what happened.

## Where we are

Built on 2026-11-26 (commit `54ad321`), `run-all.sh` green:

- the run guard (`hooks/run-guard.sh`, `at run-guard arm|status|disarm`): a session cannot end a
  turn mid-run except on `Run: WAITING` or `Run: BLOCKED`;
- `agents-core:unattended-run` (readiness check, playback and grilling, scope, decision rule),
  `agents-core:execute-parallel`, `agents-core:ask`, `Decision:` lines.

What it does not cover, from the RM-276 run of 2026-11-25 and from reading the design:

| Gap | Seen as |
|---|---|
| A session that is idle on a dead job, out of quota, or whose process died is never woken | the guard only acts when the agent tries to stop |
| After a compaction the skill text is gone until the guard catches a stop | the 22:37 compaction kept only "finish Phase 3"; the run stopped at 23:04 |
| `Run: BLOCKED` and "finished" are lines in a terminal nobody is looking at | 7 h 20 min before the owner asked "what is status" |
| The night's outcome is spread over chat, several `state.md` files and commits | `complete-task` deletes `_runs/<ID>/` at closeout |
| `at task run` knows none of `After:`, `parallel`, `unattended`, `Decision:` | it stops the whole run at the first `blocked` row |

## Facts to confirm first (Phase 0)

The design below rests on harness behaviour that the fixtures assume and nobody has observed:

1. The Stop hook payload carries `session_id` equal to `CLAUDE_CODE_SESSION_ID` of the Bash tool, and
   `last_assistant_message`.
2. `SessionStart` fires with `source: "compact"` after a compaction and `source: "resume"` after
   `claude --resume`, with the same `session_id`, and its stdout reaches the model.
3. `CLAUDE_PID` in the Bash tool environment is the session process, and is gone when the session ends.
4. `claude --resume <id> -p "<prompt>"` continues that session headless, runs the plugin hooks, and
   accepts `--permission-mode` and `--max-budget-usd`.
5. The harness scheduler (`CronCreate` / `/loop`) can fire a prompt into an idle session on an
   interval, and what it does while the session is out of quota.
6. Whether a Stop hook may start a detached process that survives the session.
7. Whether the Stop and `SessionStart` hooks fire under `claude -p`, and how a headless session can
   be made to compact (a `/compact` input, or a small `autoCompactWindow`). The end-to-end harness
   below depends on both.
8. The Stop hook payload carries the session's permission mode.
9. Whether a `claude -p` session keeps a scheduler wakeup or a background job alive after its turn
   ends (E6 and the watchdog's resume rule depend on it).

## Shared design (settled by the architecture review, 2026-11-26)

**Marker files**, all under the run-guard directory, named by session id:

| File | Written by | Holds |
|---|---|---|
| `<session>` | `at run-guard arm` | `task` / `state` target lines (as today) plus `meta<TAB>key<TAB>value` lines: `pid` (the session process), `cwd` (where the session runs; `claude --resume` and `git config` are read there), `armed` (time), `watch` (`on` with its caps, or absent) |
| `<session>.status` | `run-guard.sh` at every stop it lets through | `key=value` lines: `last_stop` (time), `kind` (`WAITING`, `BLOCKED`, `GAVE_UP` after five sent-backs, `EMPTY` for an empty last message, `DONE` when nothing is open), `text`, `transcript`, `mode` (the permission mode from the hook payload) |
| `<session>.sent/<event>` | whoever notifies | one empty file per event, created with an exclusive create; the creator sends, everyone else skips. This is the only dedupe, and it is what makes "finished" one message whether the hook or the watchdog sees it first |
| `<session>.watch` | `at run-guard watch` | the watcher's pid, exclusive create; a second watcher exits |

**Lifecycle.** The hook no longer deletes the marker when nothing is open: it writes `kind=DONE` and
treats a `DONE` marker as inactive. `at run-guard disarm`, a new `arm`, and the 14-day prune remove
the files. So the watchdog always has a marker to read.

**Shared files and lanes.** The first draft's "no shared files" was wrong: `lib/at.py`,
`hooks/run-guard.sh`, `hooks/tests/test-hooks.sh` and `unattended-run/SKILL.md` are edited by
several of Phases 1–4. Those phases are serial. Phases 5–6 touch `lib/task_run.py`, their own
module and tests; their only shared files are `lib/at.py` (the `task run` argument block only) and
`references/run-state.md` (the "Scripted driver" section only), so they form a second lane.
Every text change to `agents-core:unattended-run` that Phases 5–6 need is made in Phase 7.
Each scenario is its own file `scripts/tests/live/eN-<name>.sh`, so no phase edits another's.

## Phases

`After:` lines follow the new convention.

#### Phase 0: Spike the harness facts

After: none

- [x] A throwaway script and a real Claude Code session answer facts 1–9; each answer is one line
      with the evidence (payload dump, command, exit code) in `docs/meta/2026-11-26-run-guard-facts.md`.
      Fact 8: the Stop hook payload carries the permission mode. Fact 9: whether a `claude -p`
      session keeps a scheduler wakeup or a background job alive after its turn ends.
- [x] Each "no" names the phase it changes and how. A "no" on fact 9 moves E6 to an interactive
      session driven through a pty, or, if that cannot be scripted, to the manual run with E9.
- [x] The end-to-end harness skeleton (§"End-to-end tests") with scenario E1, which exercises the
      guard that already exists.

Checks: the facts file exists and has nine answered lines.
E2E: E1.

#### Phase 1: Marker schema, and re-inject the run after a compaction or resume

After: 0

- [x] The marker schema and lifecycle of §"Shared design": `arm` writes the `meta` lines,
      `run-guard.sh` writes `.status` at every allowed stop (including the five-sent-back and
      empty-message pass-throughs) and marks `DONE` instead of deleting; `status` and `disarm`
      know the new files.
- [x] `hooks/run-guard-remind.sh`, a `SessionStart` hook for `compact` and `resume`: when this
      session's marker has open targets, print which tasks are open, the first open row, and "load
      `agents-core:execute-plan` and resume from `state.md`". Prints nothing otherwise; always exit 0.
- [x] The open-target scan is one shared function in `hooks/lib/`, used by this hook and
      `run-guard.sh` (no second copy).
- [x] `hooks.json` entry; `build.py`; hook tests: open run prints, no marker is silent, finished run
      is silent, missing `jq` is silent, a `DONE` marker lets a stop through.

Shape: ≤ ~90 new code lines; `run-guard.sh` gives the scan away.
E2E: E2.

#### Phase 2: Tell the owner

After: 1

- [x] `git config agents.notifyCommand`, read in the session's working directory (the Stop payload's
      `cwd`; the marker is writable by the session), or `AGENTS_NOTIFY_CMD`: a program run without a
      shell that gets the title as its last argument and the body on stdin. Nothing configured means nothing
      is sent. No built-in service, no new dependency.
- [x] `at notify <title> [--event <key> --session <id>]` runs it with a 10 s timeout; a failing
      command never fails the caller. The title and body are passed as an argument and on stdin,
      never spliced into a shell string. With `--event`, it sends only if it creates
      `<session>.sent/<key>`.
- [x] `run-guard.sh` calls it when it lets a stop through as `BLOCKED` (title: task id and the
      decision text; event key: a hash of the text), `GAVE_UP`, `EMPTY`, or `DONE` ("run finished").
- [x] `agents-core:unattended-run` step 2 checks that a notify command is set and that a test
      message arrived (the owner confirms it).
- [x] The body holds task ids and the one-line reason, never file contents or secrets; the README
      says the text leaves the machine through whatever command the owner configured.

Shape: ≤ ~80 new code lines.
E2E: E3.

#### Phase 3: Morning report

After: 2

- [x] `at task report <TASK-ID>... [--since <rev>]` writes `docs/tasks_manager/_reports/<date>-<TASK-ID>.md`
      (`<date>` is the commit date of the run's `base_rev`, so a rerun on another day names the same
      file), committed with the run; `at ledger check` (agents-tasks, `sync_todo_ledgers.py`)
      accepts the directory. Content: per task its status, each phase row with its commit, verdicts
      and open count; every `Decision:`, `Ruling:` and `Note: parked:` line; for tasks already
      archived, the same lines from their completion summary; the commits recorded in the phase
      rows (with `--since`, a second section listing `<rev>..HEAD`, which depends on HEAD); and
      "needs you" first: rows that are parked or blocked now, with their reasons. An archived
      task's date comes from the `Base:` line `agents-tasks:complete-task` copies into its summary.
- [x] `agents-tasks:complete-task` copies `Note: parked:` lines into the completion summary next to
      `Ruling:` and `Decision:`, so closeout loses none of them.
- [x] Deterministic: built only from task files, run states and `git log`, so it can be run by the
      agent, by the watchdog, or by the owner, and rerun gives the same file.
- [x] `agents-core:unattended-run` step 6 runs it before closeout instead of composing the summary
      by hand, and puts the parked questions through `agents-core:ask`.
- [x] Unit tests on a fixture with one committed, one parked and one archived task.

Shape: one new module in `lib/`, ≤ ~200 code lines.
E2E: E4.

#### Phase 4: Wake a session that stopped moving

After: 3

Two layers, because the cheap one cannot see a dead process and the other must not race a live one.

- [x] **Heartbeat, in the session.** `agents-core:execute-plan` step 3, for an `unattended` task and
      where the harness has a scheduler: schedule a recurring wakeup (default every 30 min) whose
      prompt is "run guard check: if the job you are waiting for is still running, reply
      `Run: WAITING <job>`; if it died or nothing is running, resume from `state.md`". Cancelled at
      closeout. This covers a job that never reports back, and quota that returned.
- [x] **Watchdog, outside the session.** `at run-guard watch [--interval 600] [--max-resumes 4]
      [--budget-usd N] [--until HH:MM] [--idle 90]`, started detached by `at run-guard arm --watch`
      and recorded in the marker. Liveness uses `_pid_alive` from `lib/task_run.py`. Each tick:
      - `DONE` or nothing open: notify "finished" (deduped), write the report, exit;
      - last stop is `BLOCKED`: notify (deduped), do not resume;
      - session process alive: never resume. If no target file changed for `--idle` minutes, or the
        last stop is `GAVE_UP` or `EMPTY`, notify "idle" once; the heartbeat owns the waking;
      - process dead and targets open, whatever the last stop (a job the session waited on died
        with it): check the authorisation below, then `claude --resume <session> -p "<fixed prompt>"`
        in the marker's `cwd`, notify "restarted", at most `--max-resumes` times with a growing
        pause, then notify "gave up" and exit. The fixed prompt says the session is headless, that
        nothing outlives the turn, and to wait for jobs in the foreground instead of ending on
        `Run: WAITING`.
- [x] **Limits.** `--budget-usd` is the total for the watcher: each resume gets the total divided
      by `--max-resumes`. Before every resume the watcher re-reads each guarded task file and
      resumes only if it still says `Execution: unattended` and `Watch: on`. The resume uses the
      permission mode recorded in `.status`; a recorded `bypassPermissions` is refused (notify,
      exit) unless `arm --watch --allow-bypass` was given.
- [x] One watcher per session (`<session>.watch`, exclusive create); `at run-guard disarm` stops it;
      `at run-guard status` shows it.
- [x] `agents-core:unattended-run` step 4 writes `Watch: on|off`, the budget and, if granted,
      `allow bypass` into the `### Unattended run` section: restarting a dead session is an
      authorisation, given per task.
- [x] Tests with a fake `claude` on `PATH`: dead pid resumes once, live pid does not, `BLOCKED` does
      not, the resume cap holds, the budget is divided, a task no longer marked is not resumed,
      bypass is refused without the flag, a second watcher exits, `--until` ends it.

Shape: one new module in `lib/`, ≤ ~300 code lines. Security: the resume prompt is a fixed string;
the watcher takes the session id and paths only from the marker it owns.
E2E: E5, E6.

#### Phase 5: The scripted driver learns the marks

After: 0

- [x] `at task run` reads `After:` lines. A row that ends `blocked` or `parked` no longer ends the
      run: phases that do not depend on it still run; its dependants are set `parked` with a note.
- [x] With `Execution: unattended`, a phase that ends blocked is `parked` instead. A phase at the
      fix-loop cap parks unless the driver was started with `--at-review-cap continue`; then it
      commits with a `Decision:` line naming the open findings, never with a critical one. The rule
      comes only from the command line: the task file is writable by the implementers the driver
      dispatches (found in the Phase 5 reviews).
- [x] `at task run <ID> <ID>...` runs a chain in the given order, skipping a task whose `Blocked by`
      is not done.
- [x] Exit code 0 only when every row is committed; 4 when it finished with parked rows.
- [x] `test_task_run.py` cases for each bullet.

Shape: ≤ ~150 new code lines in `lib/task_run.py`.
E2E: E7.

#### Phase 6: Parallel lanes in the scripted driver

After: 5

- [x] `at task run --lanes N` (default 1, at most 3): phases whose `After:` lines are satisfied and
      whose scope fences do not overlap run at the same time, each in its own worktree and lane
      branch, one process tree per lane. A phase without a stated scope fence never shares a wave.
- [x] Bookkeeping stays in the integration checkout; the driver holds one lock for it (the existing
      run lock), so two lanes never write `state.md` at once.
- [x] Integration per wave, lowest phase first: `git merge --no-ff`; the checks from `--check` after
      each merge; a conflict or a red check parks that lane (worktree kept, noted) and the rest go on.
      The driver never resolves a conflict.
- [x] One `Stage: both` review of the wave's integrated diff before the next wave.
- [x] Merged lanes are removed (`git worktree remove`, `git branch -d`); a killed driver leaves
      worktrees that the next run finds from the `Note: lane …` lines and reuses or reports.
- [x] Tests with the fake harness: two independent phases run concurrently and merge; overlapping
      fences fall back to serial; a conflict parks one lane and commits the other; rerun after a kill.

Shape: wave planning, worktrees and merging in their own module, ≤ ~350 code lines; a lane runs the
existing phase loop through its own `Runner` on the lane worktree, no copy of that loop.
Risk: this ships merge logic before the skill-driven lanes have run on a real task. Phase 7's trial
runs the lanes through the skill first and through the driver second.
E2E: E8.

#### Phase 7: Skill text, live trial, release

After: 4, 6

- [x] `agents-core:unattended-run` step 3 asks these every time, with a recommended default:
      what to do at the review cap (recommend: park the phase, never self-rule a critical finding;
      step 4 records the answer as the `At review cap:` line, and whoever starts `at task run`
      passes it as `--at-review-cap`);
      the lane cap for the night (recommend 2); what to do when the model refuses or a safety
      classifier stops a step (recommend: route that phase to `at task run --harness codex`, else park);
      what to do when another session holds a shared resource (recommend: wait up to N minutes, then
      park).
- [x] The scripted suite E1–E8 run once from a clean checkout, output saved next to the facts file.
- [ ] Scenario E9 on one small real task in a downstream repo, with the owner present; its evidence
      goes into the facts file. It is the one step of this plan that waits for a person.
- [ ] README, seed `AGENTS.md`, CHANGELOG; `scripts/release.sh`.

Shape: text only, apart from the suite's saved output.
E2E: E1–E8 green in one run, then E9 by hand, before the release.

## End-to-end tests

Unit and fixture tests feed the hooks a payload we wrote ourselves. They cannot show that Claude
Code sends that payload, that an agent obeys a sent-back stop, or that a restarted session finds
its way. These scenarios run the real CLI against a scratch repository.

**Harness:** `scripts/tests/test-unattended-live.sh [E1 E2 …]`, built in Phase 0. It runs the
scenario files `scripts/tests/live/eN-<name>.sh`; each phase adds its own file.

- A throwaway git repo seeded with `at init --with-tasks`, the plugins loaded from this working tree,
  and a fixture task whose phases are trivial ("append a line to `a.txt`", check: `grep`), so a
  scenario costs cents and its outcome is exact.
- Real `claude -p` sessions on the cheapest model, each with `--max-budget-usd` and a timeout; its
  own `AGENTS_RUN_GUARD_DIR`, so it never touches a real marker.
- Every assertion reads files, never model prose: commits, `state.md` rows, the marker, the notify
  log, the report, the transcript's hook entries.
- Run by hand only: it needs the CLI and spends tokens, so it is not in `run-all.sh`, not in the
  pre-commit gate and not in CI. Each phase runs its own scenario before its commit and Phase 7
  runs all of them before the release. A missing CLI is a failure, not a skip.
- A scenario that fails keeps its scratch repo and transcript and prints both paths.

| # | Scenario | Passes when |
|---|---|---|
| E1 | Guard holds the turn. Two-phase task; the prompt says "do phase 1, then summarise" | the transcript shows the Stop hook sent the agent back, phase 2 is committed, and the marker is inactive after closeout |
| E2 | Compaction mid-run. Three-phase task, compaction forced after phase 1 | the reminder hook's text is in the transcript after the compaction and phases 2–3 are committed with no further prompt |
| E3 | Blocked stop notifies. A phase needs an "Owner only" action; the notify command appends to a log file | the row is `parked`, the last message has `Run: BLOCKED`, the log has exactly one line for it and one for nothing else |
| E4 | Report. Its own run with one parked row and one `Decision:`, then `at task report` | the file lists the commits, the parked question under "needs you" and the `Decision:` line; a second run of the command leaves it byte-identical |
| E5 | Dead session. `kill -9` the session after phase 1 with the watchdog armed | the watchdog resumes once, phase 2 is committed, one "restarted" and one "finished" notification are logged, and the watcher has exited |
| E6 | Dead job. The agent waits on a background job that the test kills; heartbeat interval set to 1 minute (session kind per fact 9) | within two intervals the agent stops waiting and the phase is committed or parked with the reason; a live job in the same setup is left alone |
| E7 | Driver with marks. `at task run` on a three-phase task: phase 2 cannot pass its check, phase 3 says `After: 1` | phase 3 is committed, phase 2 and nothing else is `parked`, exit code 4 |
| E8 | Driver lanes. `at task run --lanes 2`, two independent phases, then a variant where both edit the same line | both commits are on the integration branch and no lane worktree is left; in the variant one lane is parked, the other committed, and the tree is clean |
| E9 | Whole flow through the skills, in a real downstream repo, with a person present: readiness check with playback and grilling, `Execution: unattended`, two lanes through `agents-core:execute-parallel`, one authorised decision, one parked decision, closeout | the `### Unattended run` section holds the answers given, the wave was reviewed, and the committed report and the completion summary both hold the `Decision:` line and the parked question |

Negative checks, run with E1: a second session in the same repo that never armed the guard stops
freely; `at run-guard disarm` lets the armed one stop; five sent-backs in a row let the stop through.

E9 is the only scenario a person judges. The rest are scripted and repeatable.

## Order

Phase 0 first. Then two lanes: lane A is Phases 1, 2, 3, 4 in that order; lane B is Phases 5, 6 in
that order, in its own worktree. Lane B is merged into the integration branch after lane A's last
phase, with the full checks after the merge and one review of the integrated diff. Phase 7 last.

## Acceptance

The end-to-end suite E1–E8 passes from a clean checkout, and E9 was run once with its evidence
(repo, task id, transcript path) recorded in the facts file. In particular:

- A session killed with `kill -9` mid-run is resumed by the watchdog and commits the next phase.
- A session waiting on a job that was killed resumes within two heartbeats.
- After `/compact` mid-run, the next turn names the open row without the owner typing.
- `Run: BLOCKED` produces one notification within a minute; a finished run produces one.
- `at task report` on the trial run lists every commit, decision and parked question, and nothing
  that is not in the files.
- `at task run` on a three-phase fixture where phase 2 blocks and phase 3 says `After: 1` commits
  phase 3 and exits 4.
- `at task run --lanes 2` on a fixture with two independent phases finishes in less wall-clock time
  than `--lanes 1`, with both commits on the integration branch and no lane worktree left.

## Out of scope

- A hosted notification service or chat integration: the owner's command does that.
- Codex: it exposes no session id, so guard, heartbeat and watchdog stay Claude Code only; the
  driver changes of Phase 5 apply to both.
- Waking a machine that is asleep or off.

## Decisions (owner, 2026-11-26)

| # | Decision | Chosen |
|---|---|---|
| D1 | How notifications are sent | a command the owner configures per checkout; nothing built in |
| D2 | Where the report file lives | `docs/tasks_manager/_reports/<date>-<TASK-ID>.md`, committed |
| D3 | May the watchdog restart a dead session by itself | yes, only for `unattended` tasks, capped at 4 resumes and a total budget set in the readiness check |
| D4 | Parallel lanes in the scripted driver | in this plan (Phase 6), against the recommendation to wait |

---

## Execution log

- 2026-11-26: run opened (`agents-core:execute-plan`, large mode, runtime claude). Base `da43501`,
  branch `master`, work mode default-branch, autonomy L1. Run state:
  `docs/_plans/_runs/unattended-run-hardening/`. Spec source: this plan (planned intent).
- 2026-11-26: architecture review, both REVISE (plan-critic 6 blocking, Codex peer 4; see
  `architecture-review.md` and `architecture-review-peer.md` in the run directory). Plan revised:
  marker schema and lifecycle settled in §"Shared design"; Phases 1–4 serial, 5–6 a second lane;
  live suite run by hand only, one file per scenario; watchdog budget is a total, re-checks the
  task mark, refuses bypass mode without a flag; parked notes survive closeout; facts 8–9 added.
  Choices the reviews forced that the owner did not make are `Decision:` lines in `state.md`.
- 2026-11-26: Phase 0 done. Nine facts answered in `docs/meta/2026-11-26-run-guard-facts.md`
  (1-4, 6-8 yes; 5 and 9 partly: a scheduled prompt fires only in an interactive session, never
  under `-p`; `-p` stays alive for a background job but not for a scheduler wakeup). Live harness
  `scripts/tests/test-unattended-live.sh` with E1 and its negatives passes on the real CLI.
  Reviews: spec FAIL, quality FAIL (1 critical: a setup failure could start a session in the
  caller's repo), fix round 1, re-review PASS 0/0/3; minors A and B fixed by the orchestrator, C ruled.
  Size: +406 lines, all test harness and docs; flagged: none. See
  `docs/_plans/_runs/unattended-run-hardening/phase-0/`.
- 2026-11-26: Phase 5 done on lane branch `lane-b/driver` (`52e97e9`); its live scenario E7 is
  written with Phase 6, after the harness was merged into the lane. Reviews: all three FAIL at
  round 0 (1 critical: `continue` committed unreviewed edits), three fix rounds, the third
  structural: the cap rule now comes only from `--at-review-cap`, never from a file. Final: spec and
  quality PASS, security's open items closed, one more important finding fixed by the orchestrator
  (an implementer that commits aborts the run). Rulings: 5. Size: `task_run.py` +206/-37 against
  ~150, flagged and ruled. See `docs/_plans/_runs/unattended-run-hardening/phase-5/`.
- 2026-11-26: Phase 1 done. The Stop hook writes `<session>.status` and marks DONE instead of
  deleting the marker; a SessionStart `resume|compact` hook re-prints the open rows; `arm` records
  pid, cwd and time. Reviews: spec FAIL at round 0 (12 findings), one fix round, re-review PASS;
  four follow-ups and two test flakes fixed by the orchestrator (1 ruling). Live E1 found one more
  defect: stderr noise before a send-back makes the harness ignore it. Checks: test-hooks 296/0,
  test-at 348/0, run-all ok, live E1 E2 PASS. Size: net code about 85 lines against ~90.
  See `docs/_plans/_runs/unattended-run-hardening/phase-1/`.
- 2026-11-26: Phase 2 done. `at notify` runs the owner's own program (no shell, title as last
  argument, body on stdin, 10 s timeout, once per event); the Stop hook calls it detached on
  BLOCKED, GAVE_UP, EMPTY and DONE. Reviews: spec and quality FAIL at round 0 (1 critical: a failed
  send burned its dedupe key), security PASS; one fix round, re-review left 1 important, closed by
  the orchestrator. Decisions: command read in the payload's cwd, not the marker's; no shell.
  Rulings: 3. Checks: test-hooks 319/0, test-at 374/0, run-all ok, live E1 E3 PASS. Size: about 90
  code lines against ~80. See `docs/_plans/_runs/unattended-run-hardening/phase-2/`.
- 2026-11-26: Phase 3 done in a third worktree (branch `lane-c/report`, `402f1f2`; merged later).
  `at task report` in `lib/task_report.py`. Reviews: spec FAIL 0/3/3 and quality FAIL 1/6/7 at
  round 0 (the report followed HEAD and the user's git config; the report file followed a symlink);
  two fix rounds, re-review 2 PASS. Decisions: the commit list is the commits recorded in the phase
  rows, `--since` is a separate section; "Needs you" holds only what is open now. Rulings: 4.
  Checks: test_task_report 21 OK, run-all ok, live E4 PASS. Size: 182 code lines against ~200.
  See `docs/_plans/_runs/unattended-run-hardening/phase-3/`.
- 2026-11-26: Phase 6 done in the lane B worktree (branch `lane-b/driver`, `f1971f5`; merged later).
  `at task run --lanes N` in `lib/task_lanes.py`. Reviews at round 0: spec, quality and security all
  FAIL (the wave commit staged everything; a kill between merge and state save re-implemented a
  phase). Two fix rounds with a decided design: a wave is a transaction, what is committed is the
  reviewed tree, driver git calls ignore replace refs. Re-review 2: all PASS. Rulings: 7. Checks:
  test_task_run 59 OK, run-all ok, live E7 E8 PASS. Size: task_lanes.py 347 lines against ~350.
  See `docs/_plans/_runs/unattended-run-hardening/phase-6/`.
- 2026-11-26: Phase 4 done (master). Watchdog `at run-guard arm --watch` / `watch` in
  `lib/run_watch.py`, heartbeat text in execute-plan step 3, `Watch:` lines in unattended-run step 4.
  Reviews at round 0: spec FAIL (size only), quality FAIL 1/4/5, security FAIL 0/3/4 (a re-arm reset
  the restart cap and budget; the session could silence the watcher's alerts). Two fix rounds with a
  decided design: one persisted record per watched run, a re-arm can only lower caps, watcher-only
  events are not deduped through `.sent/`. Re-review 2: all PASS. Decisions: caps guard against
  accidental loops, not a session that disarms and re-arms (stated in run-state.md); module ceiling
  380 code lines instead of ~300. Rulings: 3. Checks: test_run_watch 30 OK, run-all ok, live E1 E5
  PASS; E6 heartbeat half is manual (with E9). See `docs/_plans/_runs/unattended-run-hardening/phase-4/`.
- 2026-11-26: Phase 7, the part that needs no person (master). Step 3 of `agents-core:unattended-run`
  asks the four standing questions; README, seed `AGENTS.md`, CHANGELOG and the wave-commit recovery
  in run-state.md written. Live suite E1-E5, E7, E8 green in one run from a clean checkout of
  7df6312, E6 dead-job half green; output in `docs/meta/2026-11-26-run-guard-e2e.log`. Review of the
  text: FAIL 0/3/6 (recovery steps in the wrong order and with the wrong row state; `--harness codex`
  without `--phase`), fixed by the orchestrator. A probe of the seam between phases 3 and 4 found
  that a watcher started outside the run's repository wrote no report; fixed with a test. Open and
  waiting for the owner: scenario E9, the heartbeat half of E6, and `scripts/release.sh`.
