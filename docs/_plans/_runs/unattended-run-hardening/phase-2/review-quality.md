reviewer (quality), phase 2. Verdict: FAIL, findings 1/4/4. Never-trap measured: hook wall 67 ms with a 30 s command, `{}`, exit 0, harness pipe not held. Size 76 against Shape 80.
1. [critical] lib/at.py:1493-1499: the dedupe key is created before the command is resolved or run and never removed: a failing command or no command burns the key, the same decision is never sent, and `at run-guard status` prints "notified" for a message that never left.
2. [important] scripts/tests/test-at.sh:455: the bad-key test cannot fail (log line is `bev2`, the grep is 0 either way); with the regex removed `--event '../x'` created `<guard dir>/x` and sent.
3. [important] hooks/run-guard.sh:70,72: GAVE_UP has no test: "not notified" and "relays the model message" mutations both pass.
4. [important] at.py:1513: the 10 s timeout and killpg are untested (timeout=600 passes).
5. [important] at.py:1498: a read-only guard dir means no notification at all, for the one failure that also disables the guard; test-hooks.sh:920 asserts only the exit code.
6. [minor] test-hooks.sh:910,927: positive asserts after a fixed `sleep 1`; negative asserts after `sleep 1` pass vacuously when the sender is slow. Use note_wait.
7. [minor] at.py:1500, run-guard.sh:77: `cwd.is_dir()` is redundant; the `cut -c1-200` title cap is untested.
8. [minor] run-guard.sh:14-23,47: header omits `<session>.sent/`; the write_status comment hides that it notifies; README omits EMPTY.
9. [minor] at.py:1509: `sys.stdin.read(4000)` has no timeout; `--event` without `--session` silently sends undeduped.
Outside the diff: run-guard.sh:60 prints "Permission denied" on stderr with a read-only guard dir (redirect fails before 2>/dev/null applies), on let-through paths; "remind: missing jq is silent" flakes with exit 141 under load (SIGPIPE, same cause as the phase-1 flake).
## Status: DONE_WITH_CONCERNS
## Verdict: FAIL
## Findings: 1/4/4
