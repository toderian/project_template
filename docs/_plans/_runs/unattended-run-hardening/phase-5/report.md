# Phase 5 report (implementer reply, saved by the orchestrator: the subagent could not write the file)

## Test plan
Class `Marks` in scripts/tests/test_task_run.py; an inline wrapper driver fails one quality review with a chosen severity.
- Blocked/parked row does not end the run, dependants park, exit 4: test_blocked_row_does_not_end_the_run_dependants_park_and_exit_is_4
- Not unattended: row stays blocked, exit 1, dependants parked, rerun gate and --retry-blocked: test_without_unattended_the_row_stays_blocked_exit_1_and_serial_dependants_park
- After: parsing: test_after_none_and_unknown_numbers
- At review cap: continue commits with a Decision: line: test_review_cap_continue_commits_with_a_decision_line
- park, missing key, critical finding or not unattended never continues: test_review_cap_park_missing_critical_or_not_unattended_does_not_continue
- Chain order, skip on unfinished Blocked by, exit 4 then 0: test_chain_runs_in_order_and_skips_a_task_whose_blocker_is_not_done

## Behaviour and decisions
- Unattended = Execution row or line contains `unattended`; then a phase that ends blocked is set `parked`, else stays `blocked`.
- A blocked phase's edits are kept aside: `git reset -q`, then `git stash push -u` excluding the run dir, message `at task run: <ID> phase N not finished`.
- RunError cases (timeout, baseline check failure, commit failure) still abort the run: row blocked, exit 1.
- A run ending with blocked or parked rows now commits the run dir (`chore: <ID> run state`).
- Decision: line goes into state.md, the phase commit message and the task log entry.
- Chain "done": blocker's task file Status is done (archived found too) or it exited 0 earlier in the invocation. Skip rule only with more than one ID. Chain exit: 1 if any 1, else 4 if any 4 or skipped, else 0.
- Exit codes: 0 success; 1 blocked/failed/RunError/final review failed/lock held; 2 bad args or no harness; new 4 parked rows or skipped chain task. 1 wins over 4.
- Rerun meeting blocked or parked rows without --retry-blocked skips them, runs independent phases, returns 1 if a blocked row remains else 4.

## Interface
Runner.runnable(state, pending) -> list[int]; phase_deps(task, n) -> list[int] (module level; first `After:` line in the phase body; none -> []; no line -> [n-1]).

## Checks
python3 scripts/tests/test_task_run.py: 25 OK. bash scripts/tests/run-all.sh: ok.

## Not checked
E7 live; --no-commit with dependants has no test.

## Status: DONE
