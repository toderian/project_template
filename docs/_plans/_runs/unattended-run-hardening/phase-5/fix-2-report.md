Fix round 2 (implementer reply, saved by the orchestrator). All 6 findings reported fixed, each mutation-checked; 38 tests OK; run-all ok.
1 run_policy is a module function reading the task file at base_rev from state.md (HEAD when the run opens); preflight reads every chain task's policy before the first dispatch; flag --at-review-cap park|continue overrides. No separate chain-order test.
2 Execution cell split on commas, values compared exactly; ~~~ fences, unclosed fences and HTML comments stripped.
3 may_commit_open: every open review FAIL with >= 1 parsed finding, header `N (C:x I:y M:z)` with x+y+z == N == parsed count, no critical; spaced form read; `0/1/0` or no count parks.
4 DispatchError note names the role and driver.log.
5 repeated note skipped; State.save writes nothing when only the timestamp would change.
6 run-state.md: exit 4 unattended / 1 otherwise; documents --at-review-cap, policy source, strict header.
