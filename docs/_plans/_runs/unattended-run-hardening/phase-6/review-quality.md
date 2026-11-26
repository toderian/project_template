reviewer (quality), phase 6. Verdict: FAIL, findings 2/4/4. Suite 3 runs 45 OK. Threads: each lane has its own Runner, Harness, State and index; no lock collisions in about 15 runs. Size 225 against ~350, no copy of the phase loop.
1. [critical] task_lanes.py:124-125 (no save before :200): a red check that also dirtied a tracked file the merge changed makes `git reset --keep` refuse: exit 1, the red merge stays on HEAD, state.md says rows `implementing` with no note, task file dirty; rerun 1 writes a multi-line error into the ledger, rerun 2 exits 1 with `state.md is invalid`.
2. [critical] task_lanes.py:176-200, :80: state is saved only after the whole merge loop and claim_lane treats a merged lane branch as empty: SIGTERM during the post-merge check, the rerun removes the lane and implements the phase again on top of the first merge, which never passed its check and falls outside the wave diff.
3. [important] task_lanes.py:214-216, task_run.py:874-876: a failed wave review is forgotten by a plain rerun (rows are committed; the rerun runs the final review and exits 0).
4. [important] task_lanes.py:192 vs :217-218: the task file is ticked after each merge but the ledgers sync only at wave end: a check that validates ledgers (this repo's run-all.sh) turns red for the next lane, and a reviewed lane is parked.
5. [important] task_lanes.py:173-174, :82: no process group or signal handling for lanes: SIGTERM to the driver leaves both lane harnesses alive and the lock stale; an immediate rerun runs `git worktree remove --force` under them.
6. [important] test_task_run.py:325-368: guards with no failing test (mutations stay green): lane_problem uncommitted check (:105), one-commit check (:108), unmerged-commits check in claim_lane (:80), lanes cap (:52), foreign directory at the lane path (:78); findings 1-3 have no test.
7. [minor] task_run.py:869-871: a parked lane retried with --retry-blocked as a wave of one runs serially in the integration checkout; its worktree, branch and note stay, unreported.
8. [minor] task_lanes.py:220: `git add -A -- .` in the wave commit sweeps files a check created.
9. [minor] task_lanes.py:119-121: any merge refusal is reported as a conflict; :146 a wave with nothing merged reuses its number.
10. [minor] task_lanes.py:68 repeats Runner.require_clean_tree's filter; fail() repeats set_aside's note; --dry-run does not show waves.
## Status: DONE_WITH_CONCERNS
## Verdict: FAIL
## Findings: 2/4/4
