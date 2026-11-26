# Open findings, phase 3, round 2 (see re-review-1.md)

1. [critical] N1: test helper `fail` shadows `unittest.TestCase.fail`, so most assertions cannot
   fail. Rename the helper; then run the suite and fix every assertion that was wrong all along
   (N2 at test_task_report.py:127 is one). Prove it: temporarily reverse the row order in a scratch
   copy of the module and show the row-order test fails.
2. [minor] N3: a short state row (`| 1 |`) is exit 2 with one line, not a traceback.
3. [minor] N4: check every target before writing any (all-or-nothing includes the target check).
4. [minor] N6: a Commit cell wrapped in backticks or in upper-case hex is read as a sha.
5. [minor] N7: do not force the file mode: a new report follows the umask, a replaced one keeps
   the mode it had.
6. [minor] tests for the mutations that still survive: all-or-nothing write (order the ids so the
   good one comes first), a symlinked `docs/tasks_manager`, a `parked` row (not only `blocked`),
   `Phase 1` not matching `Phase 12` lines, the missing-object note, a Commit cell that is not hex
   never reaching git, `--since` with a leading dash.

Ruled, do not fix: N5 (a ref whose name is the recorded short sha wins) and N8 (`--since` drops
empty commits).
