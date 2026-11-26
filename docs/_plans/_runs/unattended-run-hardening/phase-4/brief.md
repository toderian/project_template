# Brief: unattended-run-hardening, Phase 4: Wake a session that stopped moving (live E5, E6)

Plan: docs/specs/2026-11-26-unattended-run-hardening-plan.md. Read "## Shared design" (marker files
table), "#### Phase 4" in full (it is the phase checklist: heartbeat, watchdog ticks, limits, one
watcher per session, the skill's step 4, the tests list, Shape, Security), rows E5 and E6 in
"End-to-end tests", and docs/meta/2026-11-26-run-guard-facts.md (facts 5, 8, 9: what `claude -p`
and the scheduler really do). Phases 1 and 2 are committed: read plugins/agents-core/hooks/run-guard.sh,
hooks/lib/run-open.sh, and the run-guard block and `cmd_notify` of plugins/agents-core/lib/at.py first.

## Phase checklist
The seven checklist items of "#### Phase 4" in the plan, verbatim, plus:
- Shape: one new module in `plugins/agents-core/lib/` (≤ ~300 code lines).
- Live scenarios `scripts/tests/live/e5-watchdog.sh` (E5) and `scripts/tests/live/e6-heartbeat.sh`
  (E6). E6 needs an interactive session with a scheduler (fact 9): if it cannot be automated
  honestly, write the scenario so it FAILS with a clear "needs an interactive session" message
  rather than passing vacuously, document the manual steps in its header, and say so in the report.

## Checks
- the new unit test file, `bash scripts/tests/test-at.sh`, `bash plugins/agents-core/hooks/tests/test-hooks.sh`,
  `python3 scripts/build.py`, `bash scripts/tests/run-all.sh`: green.
- `bash scripts/tests/test-unattended-live.sh E1 E5` (and E6 if automated) on the real CLI.

## Orchestrator notes
- Work in /home/vi/work/repos/project_template on `master` (HEAD d322b16). Do NOT commit, stage,
  stash or push. Two other agents work in other worktrees and are merged later; keep to the fence.
- Scope fence: new `plugins/agents-core/lib/run_watch.py`; `plugins/agents-core/lib/at.py` ONLY the
  run-guard block (`arm --watch [--allow-bypass]`, `disarm`, `status`, `watch`; do not touch
  `cmd_notify`, the `task` dispatch or `task run`); new `scripts/tests/test_run_watch.py` (register it
  where run-all.sh lists test files, one line); `scripts/tests/test-at.sh` only for arm/disarm/status
  changes; `plugins/agents-core/skills/execute-plan/SKILL.md` (step 3, the heartbeat; keep the file
  ≤ 500 lines) and its `references/run-state.md` ("Run guard" section only);
  `plugins/agents-core/skills/unattended-run/SKILL.md` (step 4 ONLY; another agent edits step 6);
  `scripts/tests/live/e5-watchdog.sh`, `e6-heartbeat.sh`; README.md one or two lines. Do NOT edit
  `lib/task_run.py` (import `_pid_alive` from it), `scripts/tests/test_task_run.py`,
  `plugins/agents-core/hooks/*.sh`, `scripts/tests/live/lib.sh`, or `at task report` (below).
- Interface: `at task report <TASK-ID>...` is being built in parallel (phase 3) and is not in this
  checkout yet. The watcher calls it as a subprocess through the `at` binary and tolerates its
  absence or failure (log, go on); tests fake it. Do not implement it.
- Interface: `at notify <title> [--event KEY --session ID]` (body on stdin; exit 0 unless usage error
  2; dedupe by exclusive create of `<session>.sent/<KEY>`). The watcher notifies through it with
  event keys `finished`, `idle`, `restarted-<n>`, `gave-up`, `refused-<reason>`.
- Interface: marker lines `task<TAB><repo root><TAB><TASK-ID>`, `state<TAB><path>`,
  `meta<TAB>pid|cwd|armed|watch<TAB>value`; `.status` is key=value lines (last_stop, kind =
  WAITING|BLOCKED|GAVE_UP|EMPTY|DONE, text, transcript, mode), parse on `\n` only and take the FIRST
  occurrence of each key (the text line is model-derived). DONE is the only sticky inactive state;
  GAVE_UP also means "only missing state files are left". `run_guard_open` in hooks/lib/run-open.sh
  is the bash scan of what is open: the watcher needs the same answer in python; share one
  implementation if at.py already has one (`at run-guard status`), do not write a third.
- Interface (facts): the session pid is `CLAUDE_PID` (recorded as `meta pid`), not `$PPID`;
  scheduler wakeups never fire under `claude -p`; `-p` stays alive only while a background job runs:
  so the resume prompt tells the session to wait for jobs in the foreground.
- Hard rule from phase 1: a hook that prints anything to stderr before a send-back is ignored by the
  harness. You do not edit hooks; keep it in mind if you touch what they call.
- Security surface (a security review follows; design for it now). The marker, `.status` and the
  task file are all writable by the AI session being watched, and `arm --watch` is run by that
  session too. Therefore:
  - the resume prompt is a fixed string; session id and cwd come from the marker and are validated
    (id `[A-Za-z0-9._-]+`; cwd an existing directory that is a git work tree containing the guarded
    task file or state file); everything goes to `claude` as argv, never through a shell;
  - the permission mode for a resume is taken from `.status` only if it is on an allow-list
    (`default`, `acceptEdits`, `plan`); `bypassPermissions` needs BOTH `arm --watch --allow-bypass`
    (held in the watcher's own argv, not re-read from a file) AND an `allow bypass` line in the task
    file's `### Unattended run` section; any other value: notify `refused-mode`, no resume;
  - before every resume the task file is re-read: `Execution` contains `unattended` (comma-separated
    cell, exact value, as lib/task_run.py reads it) and `Watch: on`; a state-only marker (no task
    line) is never resumed, only notified;
  - "process dead" means the recorded pid is gone OR is not a claude process any more (pid reuse:
    compare `/proc/<pid>/cmdline` where /proc exists); "alive" never resumes;
  - budget: `--budget-usd` total divided by `--max-resumes`, passed as `--max-budget-usd` to each
    resume; caps are the watcher's argv, not the marker;
  - one watcher per session by exclusive create of `<session>.watch` holding its pid; a stale file
    whose pid is dead is replaced; `disarm` terminates the watcher (verify the pid is that watcher
    before signalling it); the watcher exits by itself when the marker disappears or is re-armed;
  - the watcher is detached (own session, fds closed), writes a small log next to the marker
    (`<session>.watch.log`, capped), and never touches another session's files.
- Testability: the `claude` binary is looked up on PATH (tests put a fake first); intervals and
  pauses accept small values through flags so tests take seconds; no test sleeps longer than ~2 s
  per wait and waits poll with a bound; test helpers use here-strings, not `printf | grep -q`.
- Never-trap: nothing here may make the Stop hook send back or fail; `arm` without `--watch`
  behaves exactly as before.
- Live runs: cheapest model, per-session budget cap, whole phase ≤ 10 USD, scratch repos only,
  private AGENTS_RUN_GUARD_DIR; never touch ~/.local/state/agents-template/run-guard, never signal a
  process the scenario did not start (E5 kills only the session it started, by the pid in its own
  marker). Do not use `--permission-mode bypassPermissions` or `--dangerously-skip-permissions`.
- Repo rules (AGENTS.md): python3 stdlib only; generated files via `python3 scripts/build.py`; skill
  text names skills by full `plugin:skill` id.
- If a tool refuses a write or a command, say so; do not work around a refusal.

## Report contract
Your chat reply is the report, at most 35 lines: `## Test plan` first, the tick decision table in
six lines, how each security bullet is met (one line each), files changed, check results with the
last lines of the live run, what E6 really verifies, code lines of the new module, and end with:
## Status: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
