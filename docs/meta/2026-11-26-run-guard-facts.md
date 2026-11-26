# Run guard: harness facts (Phase 0 spike)

Plan: `docs/specs/2026-11-26-unattended-run-hardening-plan.md`, "Facts to confirm first".
Observed 2026-11-26 on Claude Code 2.1.332, model `haiku` (resolved to `claude-haiku-5-5`), real sessions in
scratch git repos, plugins loaded from this working tree with `--plugin-dir`. Payload dumps and probe
scripts were kept in a temp directory, not in the repo; the decisive lines are quoted below.

How the probes read hooks (the stream names no hook command; the session transcript does): a `--settings` JSON added a Stop and a SessionStart hook that wrote their stdin
to a file; `--output-format stream-json --verbose --include-hook-events` shows every hook run, with its
`exit_code` and `stderr`, in the output stream.

## Answers

1. **Yes.** The Stop payload has `session_id` and `last_assistant_message`, and the id equals
   `CLAUDE_CODE_SESSION_ID` of the Bash tool.
2. **Yes.** `SessionStart` fires with `source: "resume"` (`claude --resume`) and `source: "compact"`
   (after compaction), same `session_id` (resume: quoted under fact 4), and its stdout reaches the model.
3. **Yes** (headless `-p`). `CLAUDE_PID` in the Bash tool env is the `claude` process and is gone after exit.
4. **Yes.** `claude --resume <id> -p "<prompt>" --permission-mode acceptEdits --max-budget-usd 0.5`
   continues the same session id headless, and the working tree's plugin hooks run in it (quoted below).
5. **Partly.** `CronCreate` exists and fires into an idle *interactive* session at the interval; under
   `-p` the process exits with the turn and the cron never fires. What it does out of quota: not observed.
6. **Yes** (headless). A Stop hook may start a detached process (`setsid nohup ... &`); it outlived
   `claude -p`, which exited in 5 s. Interactive not observed (same hook runner; no reason to differ).
7. **Yes.** Stop and `SessionStart` fire under `claude -p`. Compaction is forced headless by resuming a
   session with the prompt `/compact`. `autoCompactWindow` was not tried.
8. **Yes.** The Stop payload carries `permission_mode` (`"acceptEdits"` in the probes).
9. **Partly.** `claude -p` stays alive while a background Bash job runs and takes a new turn when the job
   ends; it does not stay alive for a scheduler wakeup. So E6's "dead job" half can run under `-p`; its
   heartbeat half needs an interactive session driven through a pty, which is scriptable up to a started turn (see fact 9 below).

## Evidence

**1, 7, 8: Stop payload.** Dump of a `-p` session (ids and paths replaced):

    {"session_id":"<session-id>","transcript_path":"~/.claude/projects/.../<session-id>.jsonl","cwd":"...","prompt_id":"...","permission_mode":"acceptEdits","effort":{"level":"medium"},"hook_event_name":"Stop","stop_hook_active":false,"last_assistant_message":"The command didn't run. ...","background_tasks":[],"session_crons":[]}

The Bash tool (a script run under `--allowedTools`) printed `SID=<session-id>`,
and the Stop payload of that session had `"session_id":"<session-id>"`. The hook
process env also holds `CLAUDE_CODE_SESSION_ID` and `CLAUDE_PID`. New fields the design can use: `prompt_id`,
`stop_hook_active`, `background_tasks` (id, type, status, command of each running job) and `session_crons`
(id, schedule, prompt of each scheduled job). The SessionStart payload is `{session_id, transcript_path, cwd,
hook_event_name, source}`; on resume it adds `seconds_since_last_response`, `context_tokens`,
`prompt_cache_likely_expired`.

**2: resume and compact.** Resume dump: `"hook_event_name":"SessionStart","source":"resume"`. The probe hook
printed `PROBE-TOKEN-7731 source=resume`; the resumed session repeated the line verbatim, so stdout reached
the model. Compact: `claude --resume <session-id> -p "/compact"` emitted `compact_boundary` and a second
SessionStart dump `{"session_id":"<session-id>","source":"compact"}`; the transcript holds
`"hookName":"SessionStart:compact" ... "rendered":[{"content":"<system-reminder>\nSessionStart:compact hook success: PROBE-TOKEN-7731 source=compact\n</system-reminder>"}]`.
Note: `hooks.json` today registers `session-drift.sh` only for the `startup` matcher; Phase 1 must add
`resume` and `compact`.

**3: `CLAUDE_PID`.** Bash tool output: `PID=<pid>`, `ps -o pid=,comm= -p <pid>` gave `<pid> claude`;
after the session ended `kill -0 <pid>` failed with `No such process`. `PPID` of the tool shell was a
different pid (the shell is a child), so the marker must store `CLAUDE_PID`, not `$PPID`.

**4: headless resume.** `claude -p --model haiku --max-budget-usd 0.5 --permission-mode acceptEdits
--plugin-dir ... --resume <session-id> -- "<prompt>"` exited 0; `system/init` showed
`"session_id":"<session-id>"`, `"permissionMode":"acceptEdits"`; the Stop hook ran again and its payload had
`permission_mode: acceptEdits`. The flags are accepted on resume. The resume ran in the original cwd; resuming from another cwd was not
tried, and the transcript store is keyed by cwd, so keep the marker's `cwd` and resume there.
Plugin hooks on resume: a session started with `--session-id` and `--plugin-dir` of this
tree, then `--resume <session-id> -p`. The `system/init` line of both runs holds the same `session_id`.
In the transcript, after the resume, the plugin's Stop hook is recorded:
`"attachment":{"type":"hook_success","hookName":"Stop","hookEvent":"Stop","exitCode":0,"command":"\"${CLAUDE_PLUGIN_ROOT}\"/hooks/run-guard.sh"}`
and `{"type":"system","subtype":"stop_hook_summary","hookInfos":[{"command":"\"${CLAUDE_PLUGIN_ROOT}\"/hooks/run-guard.sh"}]}`
(the first run of that session has the same two lines, so the hook ran in both). `run-guard.sh` exists only in
this tree, not in the installed older plugin. A sent-back is recorded in `hookErrors` with the expanded
path `["<this tree>/plugins/agents-core"/hooks/run-guard.sh]: Run guard: ...`; `live/lib.sh` reads that.

**5: scheduler.** `-p`: `CronCreate` (deferred tool, loaded via ToolSearch) returned "Scheduled recurring
job <job-id> (Every minute). Next run: 7:31am. Session-only (not written to disk, dies when Claude
exits)"; the process exited after 7 s, `cron.out` was never written. Interactive, through a python `pty`
(`pty.fork`, trust dialog answered with Down+Enter): the same job fired at the next minute, the screen
showed `Running scheduled task (Nov 26 7:35am)`, and the model began the turn (`Appending current date
to cron.out`); it then waited on a permission prompt because my allowlist did not cover the redirect, so
`cron.out` stayed empty. The Stop payload of the interactive session carried the job in `session_crons`.
Out of quota: not observed (no way to exhaust quota safely). The tool description says jobs are
session-only and expire after 30 days.

**6: detached process.** A Stop hook ran `setsid nohup bash -c 'echo $$ > pid; sleep 120' >/dev/null 2>&1
</dev/null &`. `claude -p "Say ok."` returned in 4.99 s, exit 0; afterwards `kill -0 <pid>` succeeded and
`ps` showed the `sleep` with PPID 1 and its own session. The hook must redirect all three streams, as above,
or the hook runner can wait on them (not tested without the redirect).

**9: background job and scheduler under `-p`.** Prompt: start `job.sh` (sleeps 25 s, writes a file) as a
`run_in_background` Bash job and end the turn. Result: `claude -p` ran 34 s, exited 0, and the file was
written; the stream shows `task_started`, `background_tasks_changed`, `task_notification`, a second Stop
event, and the first Stop payload had `"background_tasks":[{"id":"<task-id>","type":"shell","status":"running",...}]`.
So a `-p` session keeps a background job alive and wakes on its completion. For the scheduler, see fact 5:
`-p` exits with `session_crons` still pending. Interactive-through-pty: a scheduled turn started (see fact 5) but no scheduled turn was observed to complete. The trust dialog
defaults to "No, exit" (send Down, then Enter), the prompt and its Enter must be written as two writes with a
pause, and the child env must drop `CLAUDE_CODE_CHILD_SESSION` and the other inherited `CLAUDE_*` markers
(otherwise "Transcript saving is off").

## Consequences for later phases

| Fact | Answer | Phase | Change |
|---|---|---|---|
| 2 | yes | 1 | add `resume` and `compact` matchers for the reminder hook in `hooks.json` (today `startup` only); the hook may print plain stdout |
| 3 | yes | 1 | store `CLAUDE_PID` (not `$PPID`) as `meta pid`; liveness is `kill -0` |
| 4 | yes | 4 | the watchdog may `cd <meta cwd> && claude --resume <id> -p ... --permission-mode <mode> --max-budget-usd <n>`; the payload `permission_mode` fills `.status` `mode`. Bypass mode: not observed (the one attempt to start a `bypassPermissions` session was refused by the classifier of the session that drove the probes, not by the CLI), so do not rely on it and keep the plan's "refuses bypass mode without a flag" rule on its own merits |
| 5 | partly | 4, 7 | the heartbeat can only fire in an interactive session; a `-p` run (including the watchdog's resume) must not count on `CronCreate`. The skill text must say a scheduled wakeup dies with the process. Quota behaviour is unknown: the watchdog must assume a stopped quota looks like a dead session and rely on its caps |
| 6 | yes | 2, 4 | a hook may start the watcher with `setsid nohup ... >/dev/null 2>&1 </dev/null &`; it must redirect all streams |
| 9 | partly (the "no": a scheduler wakeup does not keep `-p` alive) | 4, E6 | E6 "dead job" runs under `-p` (the session wakes on the job's end by itself); E6 "heartbeat" needs an interactive session driven through a pty (`scripts/tests/live/e6-*.sh`, python `pty`): a scheduled turn started under the pty, but a completed one was not observed (it stopped on a permission prompt), so E6's heartbeat half is unproven and may need a wider allowlist or be manual. The watchdog may treat `background_tasks` non-empty in the last Stop payload as "waiting, alive" only while `kill -0 pid` holds |
| 7 | yes | 2 (E2) | E2 forces compaction with `claude --resume <id> -p "/compact"` between two `-p` turns |

Other observations for the harness and later phases:

- `claude -p` from inside a Claude Code session inherits `CLAUDE_CODE_*` variables; `live/lib.sh` unsets
  `CLAUDE_CODE_SESSION_ID`, `CLAUDE_CODE_CHILD_SESSION` and `CLAUDE_PID` so the guard sees only the id given
  by `--session-id`.
- `--session-id <uuid>` lets the harness arm the guard before the session starts.
- The headless Bash permission check rejects commands with variable expansion or a `bash ` prefix the
  allowlist does not match; the harness allowlists `git`, `echo`, `grep`, `cat`, `sed`, `printf` and relies
  on `acceptEdits` for file edits.
- The model is not deterministic about stopping early: with the prompt "do phase 1, then summarise" it
  sometimes does phase 2 unprompted (the guard then has nothing to do). The E1 prompt says "phase 1 only,
  then end your turn; if a Stop hook sends you back, follow it". Over two runs of the final prompt E1 passed,
  once with two sent-backs and once with one.

## Scenario E9 (manual, 2026-11-26, release 1.15.0)

One Claude Code session in a downstream repo, the owner present, two small accessibility tasks marked
through `agents-core:unattended-run`. The session ran from 15:20 to 17:10; the owner answered the
readiness questions, then came back only to ask for the pull request and to say it was merged.

What held:

- Readiness check: playback and grilling ran; the session found on its own that an open pull request
  rewrote both target files and asked where to commit. Both tasks got `Execution: unattended` and an
  `### Unattended run` section with the four standing answers (`At review cap: park`, `Lanes: 1`,
  `On refusal:`, `On shared resource:`) and a named gap (no notify command).
- Decision rule: one `Decision:` line (an existing test file extended instead of the new one the task
  named) and five `Ruling:` lines across the two tasks, each with a cost-if-wrong clause. All reached the report.
- Owner-only limits: no push, pull request or task close until the owner asked for each.
- Report: `at task report` wrote one file per task under `docs/tasks_manager/_reports/`, "Needs you:
  Nothing open", and it was committed with the run state.
- Reviews: one independent reviewer subagent per task, plus Codex reviews of the fixes.

What did not hold, all from one cause: after writing the mark the session started the work itself
and never loaded `agents-core:execute-plan` (the skill names it as "the loop" but has no hand-off step).

- The run guard was never armed: no `at run-guard arm` call, no marker for the session. A turn at
  15:51 ended on a progress summary with the test suite, two loop cells and the report still open;
  only a background job's completion brought the session back.
- The run state was written from memory: mid-run `at task run-state check` failed on status
  `reviewed` (not an allowed value) and on two commit ids in one cell. The session corrected the
  status to `committed` before the report; the report's "Commits" section stayed "None recorded".
- No heartbeat was scheduled, so the heartbeat half of E6 was not exercised.

Not covered by this run: two lanes through `agents-core:execute-parallel` (the owner chose
`Lanes: 1`), a parked decision (nothing fell outside the authorised scope), the watchdog
(`Watch: off`).

Follow-ups:

- `agents-core:unattended-run`: add an explicit step after the mark, "load `agents-core:execute-plan`
  and run through it", so the guard is armed and the run state is written by its rules. Done in 1.15.1
  (e4006c5); not yet proven in a real run.
- `at task report`: the "Commits" section is empty when the commits are in another repository's
  checkout.
- Closing a task removed the run folder with uncommitted review files in it (four Codex review files
  were lost); the closeout should refuse or commit them first.
- Repeat E9 with two lanes, one parked decision and the guard armed once the hand-off is fixed.
