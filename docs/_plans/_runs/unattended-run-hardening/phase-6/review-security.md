security-auditor, phase 6. Verdict: FAIL, findings 1/2/3. A lane implementer can get unreviewed work onto the integration branch three ways (reproduced with the fake harness).
1. [C] lib/task_lanes.py:220: the wave bookkeeping commit runs `git add -A -- .` in the integration checkout: a lane implementer that writes `<repo>/src/evil_direct.py` gets it into `chore: <ID> wave 1`; it is in no phase diff and not in wave-1/diff.patch. Fix: explicit pathspecs (run directory, task file, ledger outputs) and refuse anything else dirty.
2. [I] task_lanes.py:107,117 (also :80): the lane branch is passed unqualified and git resolves refs/tags/ before refs/heads/: a tag `at-lane/<ID>-p2` on a commit-tree commit is merged instead of the reviewed commit; the row says committed and the worktree is removed. Fix: merge the full SHA the lane Runner committed; check refs/heads/<branch> equals it and its parent is base.
3. [I] lib/task_run.py:655: what is committed is not what was reviewed: `git add -A` re-reads the lane worktree after reviews and checks; a sibling lane's background writer dropped src/late.py after the review. Fix: snapshot the tree (`git write-tree`) when the diff is taken and commit exactly that tree.
4. [M] task_run.py:486: must_not_have_committed compares SHAs only: `git symbolic-ref HEAD refs/heads/master` in a lane makes the driver's lane commit land on master. Fix: require lane HEAD to be refs/heads/<lane branch> before the commit.
5. [M] task_run.py:660, task_lanes.py:117,221: driver git calls honour hooks in the shared .git: a planted pre-commit adds files after review (class already present in serial mode). Fix: `-c core.hooksPath=/dev/null` on driver git calls.
6. [M] task_lanes.py:86: a dangling symlink at the lane path makes `git worktree add` fail with RunError: the whole run aborts instead of parking that lane.
Held: fence read at driver start; names from the id regex and an integer; rerun derives paths; argv lists only; the phase-5 gate is copied from the integration Runner.
## Status: DONE_WITH_CONCERNS
## Verdict: FAIL
## Findings: 1/2/3
