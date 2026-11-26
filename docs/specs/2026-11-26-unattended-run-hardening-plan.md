# Unattended run hardening: plan

Date: 2026-11-26. Status: decisions D1–D4 made by the owner on 2026-11-26; not started.

## Goal

A run started with `agents-core:execute-plan` on a task marked `Execution: unattended` reaches its
end, or a real owner decision, without a person watching. The owner learns within minutes when it
needs them, and reads one file in the morning to see what happened.

## Where we are

Built on 2026-11-26, uncommitted, `run-all.sh` green:

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

## Phases

`After:` lines follow the new convention; phases with no shared files can run as lanes.

#### Phase 0: Spike the harness facts

After: none

- [ ] A throwaway script and a real Claude Code session answer facts 1–6; each answer is one line
      with the evidence (payload dump, command, exit code) in `docs/meta/2026-11-26-run-guard-facts.md`.
- [ ] Each "no" names the phase it changes and how.

Checks: the facts file exists and has six answered lines.

#### Phase 1: Re-inject the run after a compaction or resume

After: 0

- [ ] `hooks/run-guard-remind.sh`, a `SessionStart` hook for `compact` and `resume`: when this
      session's marker has open targets, print which tasks are open, the first open row, and "load
      `agents-core:execute-plan` and resume from `state.md`". Prints nothing otherwise; always exit 0.
- [ ] The open-target scan is one shared function in `hooks/lib/`, used by this hook and
      `run-guard.sh` (no second copy).
- [ ] `hooks.json` entry; `build.py`; hook tests: open run prints, no marker is silent, finished run
      is silent, missing `jq` is silent.

Shape: ≤ ~60 new code lines; `run-guard.sh` net shrinks by the scan it gives away.

#### Phase 2: Tell the owner

After: 0

- [ ] `git config agents.notifyCommand` (per checkout) or `AGENTS_NOTIFY_CMD`: a command that gets
      the title as `$1` and the body on stdin. Nothing configured means nothing is sent. No built-in
      service, no new dependency.
- [ ] `at notify <title>` runs it, with a 10 s timeout; a failing command never fails the caller.
- [ ] `run-guard.sh` calls it when it lets a `Run: BLOCKED` stop through (title: task id and the
      decision text) and when the guard ends because nothing is open (title: "run finished").
      Once per event, not once per stop: the marker remembers the last one sent.
- [ ] `agents-core:unattended-run` step 2 checks that a notify command is set and that a test
      message arrived (the owner confirms it).
- [ ] The body holds task ids and the one-line reason, never file contents or secrets; the README
      says the text leaves the machine through whatever command the owner configured.

#### Phase 3: Morning report

After: none

- [ ] `at task report <TASK-ID>... [--since <rev>]` writes `docs/tasks_manager/_reports/<date>-<TASK-ID>.md`,
      committed with the run (`at ledger check` accepts the directory):
      per task its status, each phase row with its commit, verdicts and open count; every `Decision:`,
      `Ruling:` and `Note: parked:` line; for tasks already archived, the same lines from their
      completion summary; the commits since `--since`; and "needs you" first: parked questions.
- [ ] Deterministic: built only from task files, run states and `git log`, so it can be run by the
      agent, by the watchdog, or by the owner, and rerun gives the same file.
- [ ] `agents-core:unattended-run` step 6 runs it instead of composing the summary by hand, and puts
      the parked questions through `agents-core:ask`.
- [ ] Unit tests on a fixture with one committed, one parked and one archived task.

Shape: one new module in `lib/`, ≤ ~200 code lines.

#### Phase 4: Wake a session that stopped moving

After: 0, 2

Two layers, because the cheap one cannot see a dead process and the other must not race a live one.

- [ ] **Heartbeat, in the session.** `agents-core:execute-plan` step 3, for an `unattended` task and
      where the harness has a scheduler: schedule a recurring wakeup (default every 30 min) whose
      prompt is "run guard check: if the job you are waiting for is still running, reply
      `Run: WAITING <job>`; if it died or nothing is running, resume from `state.md`". Cancelled at
      closeout. This covers a job that never reports back, and quota that returned.
- [ ] `run-guard.sh` records in the marker, at each allowed stop: time, `WAITING` or `BLOCKED`, the
      text, and the transcript path.
- [ ] **Watchdog, outside the session.** `at run-guard watch [--interval 600] [--max-resumes 4]
      [--budget-usd N] [--until HH:MM]`, started detached by `at run-guard arm --watch` and recorded
      in the marker. Each tick:
      - nothing open: notify "finished", write the report, exit;
      - last stop is `BLOCKED`: notify once, do not resume;
      - session process alive: do nothing (the heartbeat owns that case);
      - process dead and targets open: `claude --resume <session> -p "<resume prompt>"` with the
        recorded permission mode and the budget, at most `--max-resumes` times with a growing pause,
        then notify "gave up" and exit.
- [ ] One watcher per session (pid file); `at run-guard disarm` stops it; `at run-guard status` shows it.
- [ ] `agents-core:unattended-run` step 4 writes `Watch: on|off` and the budget into the
      `### Unattended run` section: restarting a dead session is an authorisation, given per task.
- [ ] Tests with a fake `claude` on `PATH`: dead pid resumes once, live pid does not, `BLOCKED` does
      not, the resume cap holds, `--until` ends it.

Shape: one new module in `lib/`, ≤ ~250 code lines. Security: the resume prompt is a fixed string;
the watcher takes the session id and paths only from the marker it owns.

#### Phase 5: The scripted driver learns the marks

After: none

- [ ] `at task run` reads `After:` lines. A row that ends `blocked` or `parked` no longer ends the
      run: phases that do not depend on it still run; its dependants are set `parked` with a note.
- [ ] With `Execution: unattended`, a phase at the fix-loop cap follows the `Defaults` line for it
      (park, or continue with a `Decision:` line naming the open findings) instead of always blocking.
- [ ] `at task run <ID> <ID>...` runs a chain in the given order, skipping a task whose `Blocked by`
      is not done.
- [ ] Exit code 0 only when every row is committed; 4 when it finished with parked rows.
- [ ] `test_task_run.py` cases for each bullet.

#### Phase 6: Parallel lanes in the scripted driver

After: 5

- [ ] `at task run --lanes N` (default 1, at most 3): phases whose `After:` lines are satisfied and
      whose scope fences do not overlap run at the same time, each in its own worktree and lane
      branch, one process tree per lane. A phase without a stated scope fence never shares a wave.
- [ ] Bookkeeping stays in the integration checkout; the driver holds one lock for it, so two lanes
      never write `state.md` at once.
- [ ] Integration per wave, lowest phase first: `git merge --no-ff`; the checks from `--check` after
      each merge; a conflict or a red check parks that lane (worktree kept, noted) and the rest go on.
      The driver never resolves a conflict.
- [ ] One `Stage: both` review of the wave's integrated diff before the next wave.
- [ ] Merged lanes are removed (`git worktree remove`, `git branch -d`); a killed driver leaves
      worktrees that the next run finds from the `Note: lane …` lines and reuses or reports.
- [ ] Tests with the fake harness: two independent phases run concurrently and merge; overlapping
      fences fall back to serial; a conflict parks one lane and commits the other; rerun after a kill.

Shape: lane logic in its own module, not inside `Runner`; ≤ ~350 code lines.
Risk: this ships merge logic before the skill-driven lanes have run on a real task. Phase 7's trial
runs the lanes through the skill first and through the driver second.

#### Phase 7: Skill text, live trial, release

After: 1, 2, 3, 4, 5, 6

- [ ] `agents-core:unattended-run` step 3 asks these every time, with a recommended default:
      what to do at the review cap (recommend: park the phase, never self-rule a critical finding);
      the lane cap for the night (recommend 2); what to do when the model refuses or a safety
      classifier stops a step (recommend: route that phase to `at task run --harness codex`, else park);
      what to do when another session holds a shared resource (recommend: wait up to N minutes, then
      park).
- [ ] One small real task in a downstream repo, marked `unattended` with two independent phases:
      readiness check, run, forced compaction, a killed session, a parked decision. Each mechanism is seen working once, then the same task shape runs through `at task run --lanes 2`; the transcript paths go into the facts file.
- [ ] README, seed `AGENTS.md`, CHANGELOG; `scripts/release.sh`.

## Order

Wave 1: Phase 0. Wave 2: Phases 1, 3, 5 as lanes (no shared files), Phase 2 with them if Phase 1 has
given `run-guard.sh` its shared scan first, else after it. Wave 3: Phases 4 and 6 as lanes. Wave 4: Phase 7.

## Acceptance

- A session killed with `kill -9` mid-run is resumed by the watchdog and commits the next phase.
- A session waiting on a job that was killed resumes within one heartbeat.
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
| D3 | May the watchdog restart a dead session by itself | yes, only for `unattended` tasks, capped at 4 resumes and a budget set in the readiness check |
| D4 | Parallel lanes in the scripted driver | in this plan (Phase 6), against the recommendation to wait |
