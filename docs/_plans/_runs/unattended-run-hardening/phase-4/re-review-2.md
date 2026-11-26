reviewer (spec + quality), phase 4, re-review 2. Verdict: PASS, findings 0/1/1. N1-N10 all closed; 15 mutants of this round's guards, 15 killed; test_run_watch 30 OK.
1. [important] lib/run_watch.py:486-495 with spawn (:255-257): a watcher that refuses at start is reported wrongly by `arm --watch`. Case: record 20 restarts / 20 USD, then `arm --watch --budget-usd 0.04`: 4 of 5 runs rc 1 "the watcher did not start" (reason only in the log); 1 of 5 rc 0 "watcher pid N is running" though it had exited 2. Fix: check the merged caps in `arm` before spawn and print the reason.
2. [minor] scripts/tests/test_run_watch.py:310-318: test_two_racing_arm_watch_calls counted `s1` watchers of other suite runs (already changed by the orchestrator during the review); the fixed 0.3 s sleep remains.
## Status: DONE
## Verdict: PASS
## Findings: 0/1/1
