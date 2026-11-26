# Open findings, phase 4, round 2 (see re-review-1.md and re-review-1-security.md)

Each fix is decided. Items 1-9 each need a test that fails without the fix.

1. [important] security N1, silent second watcher. Events that end the watcher (`gave-up`, every
   `refused-*`) are never deduped: each watcher that ends for that reason says so once. `arm
   --watch` prints the restarts left from the record ("1 of 2 restarts left") and, at zero, a
   warning that the watcher will only report, with the way out (`at run-guard disarm`, then `arm
   --watch`).
2. [important] quality N1: a pause-doubling test that fails when the doubling is removed (assert
   on the logged pause or on `pause_until`, not on wall-clock gaps).
3. [minor] security N2: `--until` and `--idle` belong to each watcher's argv, not to the record.
4. [minor] quality N2: the 0.01 floor is checked on the merged caps; a watcher whose share would
   be below it refuses at start with one line.
5. [minor] quality N3: the record is range-checked with the bounds parse_caps uses, and `used`
   must be >= 0; a record that fails is a damaged record.
6. [minor] quality N4: a test for the damaged-record branch (zero restarts, one "gave up").
7. [minor] quality N5: fail closed: a task section with any `Watch:` line that is not `on` is not
   restarted.
8. [minor] quality N7: `arm --watch` and `watch` refuse to start when `cksum` is not on PATH
   (one line, usage-style exit), so the watcher never loops on a failing tick.
9. [minor] quality N9: `disarm` also removes that session's temp files (`<session>.watch.state.*`,
   `<session>.arm.*`).
10. [minor] quality N8: the `arm --watch` message for a live watcher and execute-plan step 3 say
    the same thing: the caps of a live watcher are kept; to change them, `disarm`, then `arm
    --watch`, which starts a new count.
11. [minor] quality N10: test_finding4 does not depend on a 1.5 s window (wait on a condition).
12. [minor] quality N6: readability over the number. No line over 120 characters, no reliance on
    dict order for RECORD_CAPS, no `dict(reversed(...))` trick. New ceiling for run_watch.py: 380
    code lines; use what is needed, not all of it.
