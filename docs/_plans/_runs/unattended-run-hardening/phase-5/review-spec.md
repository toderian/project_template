reviewer Stage: spec, phase 5, round 0. Verdict: FAIL, findings 0/2/2. Tests: 25 OK.
1. [important] task_run.py:575 (loop break near :559): `At review cap: continue` fires when the phase is not at the cap. Unattended, continue, quality FAIL with one [I], implementer replies BLOCKED in fix round 1 after writing src/half.py: exit 0, row committed, half.py committed unreviewed, Decision says "at the fix-loop cap". No test.
2. [important] task_run.py:739-750, :933-945 (RunError path): a row blocked by a dispatch timeout still ends the run. Phase 2 `After: none`, phase 1 implementer exceeds --timeout: exit 1, rows blocked/pending/pending, phase 2 never runs, no parked note, run dir not committed. No test.
3. [minor] task_run.py:826-828: a dependant parked by the driver stays parked after its blocker is fixed and a plain rerun; only --retry-blocked clears it and the note does not say so.
4. [minor] task_run.py:851 onward: exit 0 with rows not committed under --phase N and --no-commit; run-state.md now states "0 only when every row is committed" without the exception.
Met with tests: After: parsing, independent phase runs and dependants park, cap key rules, chain order and skip, exit 4, shape +109/-17, scope fence.
## Status: DONE_WITH_CONCERNS
## Verdict: FAIL
## Findings: 0/2/2
