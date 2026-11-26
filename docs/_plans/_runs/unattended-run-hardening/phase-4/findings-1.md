# Open findings, phase 4, round 1

Spec FAIL 0/1/7 (size only), quality FAIL 1/4/5, security FAIL 0/3/4. Read review-spec.md,
review-quality.md and review-security.md here for the reproductions. The three reports share one
cause: everything the watchdog must remember lives in one process's memory and in `arm`'s flags,
so a re-arm, a watcher restart or one `at notify` call resets it. Fix the cause.

## Decided design (settled)

A. One record per watched run: `<session>.watch.state` in the guard directory, written by the
   watcher with temp + rename, read by any later watcher of that session. It holds: the caps the
   FIRST `arm --watch` gave (max resumes, total budget, allow-bypass, until, idle), the restarts
   used, the pid of a running resume child, the last permission mode seen in `.status`, and the
   watcher-only events already sent. It is created by the first `arm --watch` and removed only by
   `at run-guard disarm` and when the watcher reports "finished". A plain `arm` never touches it.
B. `arm --watch` when a record exists: a live watcher is kept as it is. A dead one is replaced by a
   watcher that continues from the record: the used count carries over, and each cap is the LOWER
   of the record and the new flags; `--allow-bypass` is never added by a re-arm. So the path
   execute-plan step 3 prescribes (a resumed session re-arms) cannot reset anything.
C. A new watcher that finds a recorded resume child still alive (and still a claude process)
   waits for it instead of starting another.
D. Watcher-only events (idle, restarted-<n>, gave-up, refused-<why>) are deduped by the record and
   sent WITHOUT `--event`, so a pre-created key in `.sent/` cannot silence them. "finished" and
   "blocked" keep the hook's shared keys (the earlier Decision). The log records the real outcome
   of each send.
E. The mode for a restart is the mode in `.status`, else the last mode in the record, else
   `default`.
F. "Finished" needs evidence: the marker was read whole (`arm` writes the marker with temp +
   rename) and holds at least one target, and every target was read. No targets, or an unreadable
   target: look again next tick; after the idle limit, notify idle.

Residual, accepted and to be stated in run-state.md: the watched session can run `at run-guard
disarm` (which only stops the watchdog) and then `arm --watch` with new caps. The caps guard
against a run that loops by accident, not against a session that sets out to defeat them; such a
session can start `claude` itself. Do not build a defence for that.

## Findings (each with a test that fails without the fix)

1. [critical] quality 1 = security 1: caps and count reset by a re-arm. Design A, B. Tests: the
   reviewer's reproduction (a fake claude that re-arms with bigger flags, then dies) stops at the
   cap with one "gave-up"; three watchers in a row share one count.
2. [important] security 2: bypass through a re-arm. Design B.
3. [important] security 3: alerts silenced by `at notify --event`. Design D.
4. [important] quality 2: second resume while the first runs. Design C.
5. [important] quality 3: empty marker or unreadable state reads as finished. Design F.
6. [important] quality 4: the non-watcher-pid test cannot fail: assert the process is still
   running (`poll() is None`), and reap what the tests start.
7. [important] spec 1 = quality 5: size. Delete split_watch_flags + VALUE_FLAGS (use the parser),
   the macOS `ps` branch, _target_paths, the duplicate ID_RE, and whatever design A makes
   redundant. Ceiling for run_watch.py after this round: 350 code lines (the plan's ~300 did not
   count the record); say in your reply what the lines are spent on.
8. [minor] security 4: the cwd check counts only target files that exist.
9. [minor] security 5: a session id starts with an alphanumeric character (watch, arm, disarm).
10. [minor] security 6: is_watcher matches `watch` followed by the session id, adjacent.
11. [minor] security 7: design E.
12. [minor] quality 6: pids are parsed with isascii() and isdigit(); a bad `.watch` or `meta pid`
    is "unknown pid", never a traceback.
13. [minor] quality 7 = spec 3: the per-restart budget is floored to cents; a share below 0.01 is
    a usage error at arm time.
14. [minor] spec 4: `--budget-usd=4` works on `arm` (falls out of item 7).
15. [minor] quality 8, 9: the test helper uses `exec sleep`; the watcher logs the pid of a resume
    child it leaves running when it exits.
16. [minor] quality 10: tests for the cwd rule, pause doubling and "allow bypass in every open
    task"; the loser of two racing `arm --watch` calls reports that a watcher is running, rc 0.
17. [minor] spec 2: execute-plan step 3 names no product tool ("where the harness has a
    scheduler").
18. [minor] spec 5, 6: with E6_PART=dead-job the scenario's last line says that only the dead-job
    half ran and the heartbeat half is manual; the manual steps in the header are two numbered
    runs (heartbeat; live job left alone).
19. [minor] spec 8: run-state.md states the limits: liveness is the recorded pid, so an owner who
    resumes by hand should disarm first; and the residual above.
