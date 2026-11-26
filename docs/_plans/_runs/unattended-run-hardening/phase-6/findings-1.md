# Open findings, phase 6, round 1

Three reviews failed (security 1/2/3, spec 0/2/3, quality 2/4/4). Most findings share two causes:
the wave is not transactional, and the driver re-reads things an implementer can change between
review and commit. Fix the causes, not each symptom. Read review-security.md, review-spec.md and
review-quality.md in this directory for the reproductions.

## Decided design (settled; implement it, do not re-open)

A. A wave is a transaction on the integration branch.
   1. Before the first merge: write and save `Note: wave K: base <full sha>, phases a, b` in state.md.
   2. Merge lanes lowest phase first, each by the FULL SHA its lane Runner committed (never a branch
      name; verify `refs/heads/<lane branch>` resolves to that SHA and that its only parent is the
      wave/phase base). After each merge run the `--check` commands; red check or any failure:
      `git reset --hard <sha before this merge>`, park that lane, go on. A merge that does not start
      is reported as "merge refused: <git's last line>", a real conflict as a conflict (aborted).
   3. Wave review of `base..HEAD`. FAIL or critical: `git reset --hard <wave base>`, every lane of
      the wave is parked (unattended) or blocked, lane worktrees and branches kept, a `Note:` says so;
      nothing of a failed wave stays on the integration branch. Exit code as for any parked/blocked row.
   4. PASS: only now tick the task file, run the ledger sync, set rows `committed` with SHAs, save
      state.md, make ONE bookkeeping commit with explicit pathspecs (run directory, task file, the
      ledger files the sync writes), append `Note: wave K: done`, then remove merged lanes.
      Anything else dirty in the integration checkout at that point is not committed: the wave is
      undone as in 3 with a note naming the stray paths (an implementer wrote outside its lane).
   5. A wave with nothing merged does not consume a wave number.
   `git reset --hard` is acceptable here because the driver refuses to start on a dirty tree, and
   because every reset target is a SHA the driver recorded itself.

B. Rerun after a kill: at the start of EVERY run of the task (with or without `--lanes`, also
   `--phase N`), the driver (a) finds a `Note: wave K: base` without its `done` line: it stops with
   exit 1 before any dispatch and prints the exact recovery (`git reset --hard <base>` when HEAD is
   past the base, then rerun); it resets nothing by itself; (b) lists every lane worktree and
   `at-lane/<ID>-p*` branch of this task from `git worktree list` and `refs/heads/`: a phase that
   has one is not run serially; a leftover that is clean and holds no commit is removed and reused;
   one that holds work is reported, its row parked, nothing deleted. A phase is never implemented a
   second time on top of its own earlier merge.

C. What is committed is what was reviewed (lane and serial mode alike, in task_run.py): when the
   review diff is packaged, record the tree (`git add -A` restricted as today, then `git write-tree`);
   just before the phase commit compute it again; a different tree blocks/parks the row with
   "the tree changed after review" instead of committing. In a lane, also require
   `git symbolic-ref HEAD` to be `refs/heads/<lane branch>` before the commit.

D. Signals: SIGTERM is handled like Ctrl-C; each lane harness runs in its own process group and
   the driver terminates those groups when it is interrupted, then releases the lock. A rerun never
   removes a worktree while a process of the dead run may still write to it: if the lock names a
   dead pid, removal of leftover lanes still follows rule B (only clean and empty ones).

## Findings to close (each with a test that fails without the fix)

1. [critical] security 1 + quality 8: wave commit used `git add -A`: design A4.
2. [critical] quality 1: red check dirtying a tracked file: design A2 (reset --hard, state saved).
3. [critical] quality 2 + spec 2: kill between merge and state save re-implements the phase: A1, B.
4. [important] security 2: unqualified branch name resolves a tag first: A2.
5. [important] security 3 + security 4: commit differs from the reviewed tree; symbolic-ref HEAD: C.
6. [important] spec 1 + quality 7: leftovers unreported on a serial rerun or --retry-blocked: B.
7. [important] quality 3: failed wave review forgotten by a rerun: A3.
8. [important] quality 4: task file ticked before the ledger sync: A4.
9. [important] quality 5: SIGTERM leaves lane harnesses alive: D.
10. [important] quality 6: guards without a failing test (uncommitted-leftovers check, one-commit
    check, unmerged-commits check, lanes cap, foreign directory at the lane path): one test each,
    or delete a guard the design above makes redundant.
11. [minor] security 6: a dangling symlink at the lane path parks that lane instead of aborting the run.
12. [minor] spec 3, 4: the wave review prompt names each phase's `Files:` fence and the paths a
    lane changed outside it; every `Files:` line of a phase is read, not only the first.
13. [minor] spec 5: e8-driver-lanes.sh main case asserts that lanes really ran (merge commits or
    the wave directory).
14. [minor] quality 9, 10: no duplicated clean-tree filter or park note (call the Runner's);
    `--dry-run` prints the planned waves.

Ruled, do not fix: security 5 (driver git calls honour hooks in the shared .git): the repository's
own pre-commit gate must keep running on driver commits; a planted hook needs a write to .git, which
is outside what the driver can defend.

Size: task_lanes.py is 225 lines against a Shape of about 350. The design replaces code (the
per-merge bookkeeping, the keep-reset, claim_lane's ancestry guess); it should not simply add.
