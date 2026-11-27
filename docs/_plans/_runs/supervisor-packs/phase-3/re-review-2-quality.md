Re-review round 2, phase 3 (quality). 1: open (see finding 1). 2-5: resolved.

## Status: DONE_WITH_CONCERNS
## Verdict: FAIL
## Findings: 3 (C:1 I:0 M:2)
1. [C] plugins/agents-core/lib/sup_watch.py:300 — `"claude" in reason` counts a pack-edge refusal as a claude failure when the pack name or task file name contains `claude`: after three tries the start is never tried again.
2. [M] plugins/agents-core/lib/sup_watch.py:289,300 — a refusal before claude keeps the `n` of earlier claude failures (15 minutes, or never).
3. [M] plugins/agents-core/lib/sup_watch.py:288-289 — a watch.json written before the change has no backoff entry for a refused task; `not bo` skips it for ever.

Fix round 3 (orchestrator, at the cap): 1 the claude failure is recognised by the three texts sup_workers' start
raises; 2 a refusal before claude sets n to 0; 3 a missing entry is retried. Test:
test_a_refusal_that_only_names_claude_is_not_a_claude_failure_and_an_old_memory_is_retried. Also the flaky
test_an_untrusted_workspace_switches_the_profile_to_headless... now holds its fake worker alive across both steps.
