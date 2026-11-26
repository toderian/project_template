# Brief: unattended-run-hardening, Phase 2: Tell the owner (notifications, live E3)

Plan: docs/specs/2026-11-26-unattended-run-hardening-plan.md. Read "## Shared design" (marker
files table), "#### Phase 2" and row E3 with the harness description in "End-to-end tests".
Phase 1 is committed (721558a): read plugins/agents-core/hooks/run-guard.sh, hooks/lib/run-open.sh
and the run-guard block of plugins/agents-core/lib/at.py before designing.

## Phase checklist
- `git config agents.notifyCommand`, read in the marker's `cwd`, or `AGENTS_NOTIFY_CMD`: a command
  that gets the title as `$1` and the body on stdin. Nothing configured means nothing is sent. No
  built-in service, no new dependency.
- `at notify <title> [--event <key> --session <id>]` runs it with a 10 s timeout; a failing command
  never fails the caller. The title and body are passed as an argument and on stdin, never spliced
  into a shell string. With `--event`, it sends only if it creates `<session>.sent/<key>`
  (exclusive create).
- `run-guard.sh` calls it when it lets a stop through as `BLOCKED` (title: task id and the decision
  text; event key: a hash of the text), `GAVE_UP`, `EMPTY`, or `DONE` ("run finished").
- `agents-core:unattended-run` step 2 checks that a notify command is set and that a test message
  arrived (the owner confirms it).
- The body holds task ids and the one-line reason, never file contents or secrets; the README says
  the text leaves the machine through whatever command the owner configured.
- Shape: ≤ ~80 new code lines.
- Live scenario `scripts/tests/live/e3-notify.sh` (E3): a phase needs an "Owner only" action; the
  notify command appends to a log file; passes when the row is `parked`, the last message has
  `Run: BLOCKED`, the log has exactly one line for it and one for nothing else.

## Checks
- `bash plugins/agents-core/hooks/tests/test-hooks.sh`, `bash scripts/tests/test-at.sh`,
  `python3 scripts/build.py`, `bash scripts/tests/run-all.sh`: green.
- `bash scripts/tests/test-unattended-live.sh E1 E2 E3` on the real CLI.

## Orchestrator notes
- Work in /home/vi/work/repos/project_template on `master`. Do NOT commit, stage, stash or push;
  the orchestrator commits. Autonomy L1.
- Scope fence: `plugins/agents-core/hooks/run-guard.sh`, `plugins/agents-core/hooks/tests/test-hooks.sh`,
  `plugins/agents-core/lib/at.py` (a `notify` command and the run-guard block only; do NOT touch the
  `task run` usage block), `scripts/tests/test-at.sh`, `plugins/agents-core/skills/unattended-run/SKILL.md`
  (step 2 only), `plugins/agents-core/skills/execute-plan/references/run-state.md` ("Run guard"
  section only), `README.md`, `scripts/tests/live/e3-notify.sh`, `scripts/tests/live/lib.sh` only if a
  shared helper is unavoidable. Do NOT edit `plugins/agents-core/lib/task_run.py`,
  `scripts/tests/test_task_run.py` or other live scenario files: another lane is editing them.
- Interface: the hook's `write_status <kind> <text>` is the one place `.status` is written; `.status`
  kinds are WAITING | BLOCKED | GAVE_UP | EMPTY | DONE; DONE is the only sticky inactive state;
  GAVE_UP also covers "only missing state files are left" and "count file unwritable".
- Interface: marker lines `meta<TAB>pid|cwd|armed<TAB>value`; `task<TAB><repo root><TAB><TASK-ID>`.
- Interface (hard rule, found by live E1): anything a hook prints to stderr before its send-back can
  make the harness ignore the send-back ("No such file or directory" reads as a missing hook
  script). The notify call must print nothing, on any path, and must never change the hook's exit
  code or delay it noticeably: decide deliberately whether the hook waits for the command (10 s
  timeout) or detaches it, and say which in the report.
- Never-trap rule: no notify failure (no command, timeout, non-zero, unwritable `.sent`, missing
  python3 or `at`) may turn a let-through stop into a send-back or an error.
- Security surface: the configured command is run by the owner's choice, but title and body come
  from model text and task ids: argv and stdin only, no `sh -c` with interpolated text, no `eval`;
  the event key is a hash, never raw text in a file name; DONE is sent once per arm (`.sent` is
  cleared by a new `arm`); a session cannot make the hook notify for another session.
  `git config` is read with `git -C <cwd>`; a marker `cwd` that is not a directory means no send.
- Lessons from phase 1's review: text taken from the model is flattened to printable ASCII and
  capped before it is used; tests feed the hooks payloads in a temp `AGENTS_RUN_GUARD_DIR`; test
  helpers use here-strings, not `printf | grep -q` (SIGPIPE under pipefail); every new behaviour
  has a test that fails without it.
- Live runs: cheapest model, per-session budget cap from lib.sh, whole phase ≤ 6 USD, scratch repos
  only, private AGENTS_RUN_GUARD_DIR; never touch ~/.local/state/agents-template/run-guard.
- Repo rules (AGENTS.md): bash, python3 stdlib, jq only; generated files only via
  `python3 scripts/build.py`; skill text names skills by full `plugin:skill` id.
- If a tool refuses a write or a command, say so in the report; do not work around a refusal.

## Report contract
Your chat reply is the report, at most 30 lines: `## Test plan` first, design in four lines (where
the command is read, wait or detach, dedupe, what the body contains), files changed, check results
with the last lines of the live run, net new code lines, and end with:
## Status: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
