## Test plan

| Behaviour (phase checklist) | Lowest layer | Test |
|---|---|---|
| Guard holds the turn, phase 2 committed, marker inactive | real CLI, `-p` session in a scratch repo | `scripts/tests/live/e1-guard-holds.sh` main scenario |
| Unarmed session stops freely | real CLI | E1 negative 1 |
| `at run-guard disarm` lets the armed session stop | real CLI | E1 negative 2 |
| Five sent-backs in a row let the stop through | real CLI | E1 negative 3 (exactly 5 exit-2 Stop hooks, then exit 0) |
| Facts 1-9 | throwaway probes, real sessions | answers in `docs/meta/2026-11-26-run-guard-facts.md` |

Fixtures: none in the repo; the scratch repos are built at run time by `live/lib.sh`.

## Status: DONE

Summary: nine facts answered with evidence; live harness and E1 (with its three negative checks) written and passing against the real CLI.

## What I did

- Probed with `claude -p` (model `haiku`, `--max-budget-usd` 0.3-1, `timeout`, scratch repos, `--plugin-dir` for the working tree)
  and one pty-driven interactive session. Probe scripts and payload dumps stayed in the scratchpad directory.
- Wrote the harness `scripts/tests/test-unattended-live.sh [E1 ...]`, shared helpers `scripts/tests/live/lib.sh`
  and scenario `scripts/tests/live/e1-guard-holds.sh`. Each session has its own `AGENTS_RUN_GUARD_DIR` under a
  scratch dir, never `~/.local/state`. A failing scenario keeps its scratch dir and prints the path. A missing
  CLI fails.
- The working-tree Stop hook ran: the sent-back `stderr` in the stream starts with `Run guard: this session is
  executing a run ...` (the installed older release has no run-guard); E1 asserts it.

## Checks

- `bash scripts/tests/test-unattended-live.sh E1`: passed on both runs of the final prompt
  (earlier failures were prompt wording, see below). Last lines of the final run:
  ```
  E1 negative 1 (unarmed stops freely): ok
  E1 negative 2 (disarm): ok
  E1 negative 3 (five sent-backs): ok
  PASS E1
  test-unattended-live: ok (E1)
  ```
- Facts file has nine answered lines (`grep -c '^[0-9]\. \*\*'` gives 9).
- `bash scripts/tests/run-all.sh`: `run-all: ok`.

## The nine answers

1 yes. 2 yes. 3 yes (`-p`). 4 yes. 5 partly (fires in an interactive session, not under `-p`; out-of-quota not observed).
6 yes (headless). 7 yes (`-p "/compact"` on a resumed session forces compaction). 8 yes (`permission_mode`).
9 partly (`-p` keeps a background job alive and wakes on its end; it does not wait for a scheduler wakeup).
E6's heartbeat half can be scripted through a python `pty` session (it worked: trust dialog needs Down+Enter,
prompt and Enter written separately, inherited `CLAUDE_CODE_*` vars dropped), about 3 minutes per run; its
dead-job half runs under `-p`. So E6 need not be manual.

## For later phases

- `hooks.json` registers the reminder hook for `startup` only; Phase 1 adds `resume` and `compact` (both fire, same session id, stdout reaches the model).
- Marker `pid` must be `CLAUDE_PID`, not `$PPID`.
- Stop payload also has `background_tasks`, `session_crons`, `prompt_id`, `stop_hook_active`; usable by the watchdog.
- A `bypassPermissions` headless session was refused by the auto-mode classifier on this machine; I did not work around it.
- E1 asserts the marker is "absent or `.status` has `kind=DONE`" (`marker_inactive` in lib.sh), so it survives the Phase 1-2 lifecycle change. E1 uses a `state` target, not a `task` target.
- E1 is model-dependent: the prompt that said "phase 1 only, then summarise" made the agent refuse phase 2 even when sent back; "do the run, then summarise" made it sometimes finish without a stop. Final prompt: phase 1 only, end the turn, "if a Stop hook sends you back, follow it". It passed 2 of 2 runs (2 and 1 sent-backs). Expect occasional flake; rerun before blaming the guard.
- Each full E1 run costs about 5 sessions on haiku, cents in total. Whole phase spend is well under 1 USD.

## Files changed

- `docs/meta/2026-11-26-run-guard-facts.md` (new)
- `scripts/tests/test-unattended-live.sh` (new)
- `scripts/tests/live/lib.sh`, `scripts/tests/live/e1-guard-holds.sh` (new)

Not checked: out-of-quota behaviour of the scheduler (fact 5); a Stop hook starting a detached process in an interactive session; `autoCompactWindow`; Codex.
