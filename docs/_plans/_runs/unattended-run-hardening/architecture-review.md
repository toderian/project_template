plan-critic (claude subagent), 2026-11-26. Verdict: REVISE, 6 blocking.
- B1 `After:` lines and Order claim "no shared files"; at.py, unattended-run/SKILL.md, run-guard.sh, test-hooks.sh, test-unattended-live.sh are shared across phases 1-5. Phase 2 needs 1; Phase 4 needs 1 and 3; E4 needs Phase 2's E3.
- B2 Live suite gated on diff inside run-all.sh runs in pre-commit and spends tokens; test-codex-live.sh is hermetic, the analogy is false. E9 needs a person, so "E1-E9 green in one run" is impossible.
- B3 run-guard.sh:67-70 deletes the marker at finish, breaking notify dedupe and the watchdog's finished tick; two actors would send "finished".
- B4 Marker has no pid, cwd or permission mode; resume mode source unspecified (bypass-mode resume is the main security risk).
- B5 Five-sent-back and empty-message pass-throughs are never notified and never woken.
- B6 E6 and WAITING-after-resume assume a live session that `claude -p` does not keep.
Non-blocking: Defaults line is prose, the driver cannot parse it; date in report filename breaks idempotence over midnight; at ledger check lives in agents-tasks; which git config wins for notify across checkouts; title must be argv not shell; budget per resume vs total; "uncommitted" is stale; reuse _pid_alive (task_run.py:42) and the lock (:443); Shape lines missing for 2, 5, 7; Phase 6 "not inside Runner" doubtful.
## Status: DONE_WITH_CONCERNS
## Architecture verdict: REVISE
## Blocking findings: 6
