Re-review round 1, phase 2 (quality, spec items included).
1: open — refused only when the holding profile has `hub` in its config. 2-9: resolved.

## Status: DONE_WITH_CONCERNS
## Verdict: FAIL
## Findings: 3 (C:0 I:2 M:1)
A. [I] plugins/agents-core/lib/sup_workers.py:423 — `pack_for_land` never matches a profile with no configured hub; fail closed.
B. [I] plugins/agents-core/lib/sup.py:270 and :253 (base code) — `--grep="Archive: refs/archive/task/<ID>"` is a substring match: TST-1 matches the commit of TST-10 (probe: TST-1 "landed" with no squash, branch deleted).
C. [M] plugins/agents-core/lib/sup_workers.py:426 — `len(held) > 1` refuses even with the right `--profile`.
Size: the fix only added code; 12-14 lines recoverable by merging `_pack_ready_lines` into `_pack_repo_problems`; the rest
answers findings the ceiling did not count.

Fix round 2 (orchestrator): A a profile with no usable hub counts as this hub; B `sup_state.landing_message` matches the
whole `Archive:` line and serves `landed`, the `done` test in `cmd_land` and the tips; C the `len` clause is gone.
Tests added: test_a_task_whose_id_is_a_prefix_of_a_landed_one_still_gets_its_own_commit, and the hub-less case in
test_a_landing_without_the_holding_profile_refuses_and_changes_nothing.
