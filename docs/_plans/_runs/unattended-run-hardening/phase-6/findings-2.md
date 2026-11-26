# Open findings, phase 6, round 2

Spec and quality passed (re-review-1.md, 0/3/4); security failed (re-review-1-security.md, 1/1/0).
Each fix below is decided. Each needs a test that fails without it. task_lanes.py is at 333 lines
against a Shape of about 350: do not pass 350; where a fix adds a guard, look for one it replaces.

1. [critical] security 1, replace refs. Every git call the driver makes (the `git()` wrappers in
   task_run.py and task_lanes.py, and the calls that build diff.patch and the size table) runs with
   `GIT_NO_REPLACE_OBJECTS=1` in its environment: set it once, where the driver builds the
   environment for git, not per call. Test: serial mode, the fake implementer runs `git replace`
   as in the reproduction; the diff the reviewer is given shows the real content.
2. [important] security 2, forged lane commit. The commit that is merged is bound to what was
   reviewed: verify() also requires `git rev-parse <commit_sha>^{tree}` == the reviewed tree
   recorded for that lane (parent == base stays). With tree and parent fixed, a forged commit can
   differ only in its message. Test: a lane branch moved to a commit-tree forgery with parent ==
   base before the SHA is read: the lane is parked, nothing merged.
3. [important] quality N1, "done" before the bookkeeping commit. The bookkeeping commit's return
   code is checked (commit_run_dir too). When it fails: state.md is written back to the text it
   had before the "done" lines, the staged ledger paths are unstaged, the run exits 1 naming the
   failed commit, and a rerun sees an open wave. Test: a pre-commit hook that rejects the wave
   commit; then the rerun stops with the open-wave message instead of exiting 0.
4. [important] quality N2, files a check creates. Before each merge the driver records the set of
   untracked, non-ignored paths; undoing that merge removes the paths that are new since then, so
   a red check's leftovers do not count as stray writes against the other lanes. Test: the
   reproduction (check red on phase 3 also writes junk.txt): phase 3 parked, phase 2 committed.
5. [important] quality N3, stray edit to a tracked file. Before a stray-write undo, the driver
   saves `git diff` of the stray paths to `wave-K/stray.patch` in the run directory and the note
   names that file; the note no longer says "left in place" for tracked files. Test: the
   reproduction; the patch holds the overwritten content.
6. [minor] quality N4: "the tree changed after review" names the paths that differ
   (`git diff --name-only <reviewed tree> <tree now>`), at most five.
7. [minor] quality N5: a leftover lane whose phase row is `committed` and whose branch tip is an
   ancestor of HEAD is removed (worktree and branch), not reported.
8. [minor] quality N6: an interrupt exits 130 as before this phase; SIGTERM exits 143. run-state.md
   says so.
9. [minor] quality N7: delete the assertion at scripts/tests/test_task_run.py:370 that cannot fail.
