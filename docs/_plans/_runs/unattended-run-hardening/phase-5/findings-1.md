# Phase 5, open findings for fix round 1

Sources: review-spec.md, review-quality.md, review-security.md in this directory (read them for
line numbers and the reproduced scenarios). Every fix needs a test that fails without it.

1. [C] `At review cap: continue` must apply only when the loop really reached the cap with a
   reviewed last round. A fix round whose implementer returns BLOCKED / NEEDS_CONTEXT / no status
   blocks or parks the row and commits nothing. (quality 1, spec 1, security 2)
2. [I] The "no critical" gate must fail closed: use the review's `## Findings:` header as well as the
   numbered lines; park when the header reports a critical or its count differs from the parsed
   count. (security 1)
3. [I] Read `Execution: unattended` and `At review cap:` once at run start from the committed task
   file (the run's base revision), not from the working tree after implementers ran. Match only the
   metadata row / the `### Unattended run` section, not fenced examples or negations. (security 3, 5)
4. [I] A `post_phase_checks` failure stops the run with exit 1, as before the change. (quality 2, security 4)
5. [I] The run-state commit never includes anything but the run directory and the task file
   (explicit pathspecs), and the user's staged work is untouched. (quality 3)
6. [I] A row the driver parked only because of a dependency is re-evaluated on a rerun once that
   dependency is committed; rows parked for their own reason stay parked. Distinguish the two in
   the note. (quality 4, spec 3)
7. [I] The stash name goes into the row's `Note:` line in state.md (and the "fix by hand" text says
   where the work is); a failing `git stash` blocks the run with a clear message. (quality 5)
8. [I] A RunError (timeout, dispatch failure) on one phase is handled like any other blocked row:
   work set aside, dependants parked, independent phases still run, run directory committed.
   Baseline-check and commit failures may still abort; say which in run-state.md. (spec 2, quality 7)
9. [M] `After:` with an unknown phase number or a cycle is an error reported before any phase runs
   (exit 2), not a silent drop. (quality 6)
10. [M] Validate every task id (`[A-Z][A-Z0-9]*-\d+`) and that its file exists before the first
    task of a chain runs. (security 7, quality 7)
11. [M] The `Decision:` line and commit message name each open finding by severity, stage and review
    file path, not by quoting its text. (security 6)
12. [M] run-state.md: state the exit-0 exceptions (`--phase N`, `--no-commit`); a chain treats a task
    as done for `Blocked by` only when all its rows are committed. Drop the needless
    `--retry-blocked` in test_blocked_row... (spec 4, quality 8)
