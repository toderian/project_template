# Phase 5, fix round 1: open findings

Sources: review-spec.md (S), review-quality.md (Q), review-security.md (X).

Required shape first. The invariant is: hub content behind a `local` entry is never deleted, replaced or
committed. It has three guards, each one place:
(a) `_link_local` makes a link only when git in the TASK WORKTREE ignores the link's path
    (`git -C <worktree> check-ignore -q -- <entry without trailing />`); otherwise Refused naming the entry and
    saying what to write in `.gitignore` of the branch. This replaces guessing from the hub's state.
(b) `cmd_land`, with its other pre-checks and before `squash_and_commit`: read the `local` list once (no
    `check-ignore` there; only the shape rules), and refuse when the task branch tracks a path equal to a `local`
    entry (`git ls-tree` of the branch tip for each entry, or one `git ls-files` call): "branch tracks the local
    path <entry>; remove it from the branch". Nothing is committed in that case.
(c) `kept_ignored` skips only a link that resolves to a `local` hub path (as now).
The hub-side `git check-ignore` in the validator stays for `at sup init` as an early hint, but a pass there is
not what protects the hub.

1. [C] Q1, S1: guard (a), with tests: `.gitignore` `shared/` plus an existing hub directory -> start-worker
   Refused naming the entry, no link left; a branch whose `.gitignore` lacks the entry -> Refused. Guard (b)
   with a test: a branch that tracks `shared` (a committed symlink) -> `at sup land` refuses before any commit,
   the hub directory and its file are intact, the hub has no new commit.
2. [I] Q3, X4: the landing reads `local` before the commit (part of (b)); remove the try/except and the
   "commit is made; rerun" message for this cause.
3. [I] Q2: pin the skip rule in test_sup_land.py: a link retargeted elsewhere and a link of an entry dropped
   from the profile are in `kept/<ID>` after landing, as links; nothing behind them is touched.
4. [I] S2, Q4: OSError from `mkdir`/`symlink_to` in `_link_local` becomes Refused naming the path. Test: a file
   at a parent of the link.
5. [I] S3: test the "would lie outside" refusal: the worktree has `d` as a symlink to another directory, entry
   `d/x/`; nothing is created behind the link.
6. [I] X1: older defect in `cmd_land`'s move loop (sup.py:285-288), fixed here because the phase adds links to
   worktrees: before moving a kept file, require that the real path of the destination's parent is inside the
   `kept/<ID>` directory; otherwise refuse naming the path. Test: `kept/<ID>/a` is a symlink to an outside
   directory (left by an earlier failed landing), the worktree has a real `a/f`: landing refuses and the outside
   directory gains no file.
7. [M] Q5, X3: validator: refuse an entry that starts with `:`; refuse a list in which one entry is a parent of
   another; `git check-ignore` exit status other than 0 or 1 is reported with git's own last line, not as "is
   not ignored".
8. [M] Q6: a malformed profile.json read by `profile_local` is reported with the file name.
9. [M] S4: supervise/SKILL.md: say plainly: write `lab-results`, not `lab-results/`, in `.gitignore`, because the
   task worktree holds a link, not a directory; and that the line must be in the branch the task starts from.
10. [M] S5: test_sup_tick.py: the `.local/repos.map` case passes a list; add a backslash and a control-character
    case; assert the new prompt sentence in the existing prompt test (test_sup_workers.py).
Ruled, not in this round: S6 (`at sup land` by hand without a profile keeps the link itself in `kept/<ID>`; the hub
content is intact); X2 (race between listing and move; workers run as the owner).
