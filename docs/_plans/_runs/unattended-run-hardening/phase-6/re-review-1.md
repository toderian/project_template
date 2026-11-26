reviewer (spec + quality), phase 6, re-review after fix round 1. Verdict: PASS, findings 0/3/4. Suite 56 OK twice (90 s, 93 s); 12 mutants of the new guards all killed. Round-0 findings 2, 3, 6, 7, 8, 9, 10, 11, 12, 14 closed by reproduction; 13 closed by reading e8 (not run live).
N1. [important] lib/task_lanes.py:304-310: `Note: wave K: done` and `committed` rows are saved before the bookkeeping commit. Case: the pre-commit gate rejects the wave commit: exit 1, state.md says done; a rerun exits 0; ledger files stay staged. Same root: commit_run_dir (task_run.py:1003-1005) ignores the commit's return code.
N2. [important] task_lanes.py:169-177, :286: the undo leaves untracked files a check created; the stray rule then undoes the whole wave. Case: a red check on phase 3's merge also writes junk.txt: phase 3 parked, then phase 2 (green, review PASS) undone and parked.
N3. [important] task_lanes.py:287-290: the stray note says "left in place, uncommitted", but the undo's `checkout <base> -- .` reverts a stray edit to a tracked file; no copy kept.
N4. [minor] task_run.py:694-699: "the tree changed after review" names no path and no cause.
N5. [minor] task_lanes.py:311-313, :134: a kill between the bookkeeping commit and lane removal: lanes of a closed wave are reported as holding work on every later run.
N6. [minor] task_run.py:1106-1108: serial Ctrl-C exits 1 instead of 130.
N7. [minor] scripts/tests/test_task_run.py:370: an assertion that can never fail.
## Status: DONE
## Verdict: PASS
## Findings: 0/3/4
