reviewer (spec + quality), phase 4, re-review 1. Verdict: FAIL, findings 0/1/9. test_run_watch 25 OK, run-all ok; 43 mutants, 38 killed. Findings 1, 4, 5, 6, 7, 12, 14, 15, 17, 18, 19 closed; 13 closed at arm time, open through the merge (N2); 16 open in part (N1).
N1. [important] scripts/tests/test_run_watch.py:265-269: the pause-doubling test cannot fail (mutant `pause * 2 ** used` -> `pause` survived).
N2. [minor] lib/run_watch.py:259-262 vs :91: the 0.01 floor is checked on the new flags, not on the merged record: record 20 / 4 USD, later watcher --budget-usd 0.04: every restart got 0.00.
N3. [minor] run_watch.py:246: the record is type-checked, not range-checked (`used: -50` gave 11 restarts titled "-39/2").
N4. [minor] run_watch.py:257-258: the damaged-record branch has no test (mutant `return fresh` survived).
N5. [minor] run_watch.py:281: `Watch: on` on any line wins over a `Watch: off` line.
N6. [minor] run_watch.py:51,101,149,154,253,291,468: 350 was met partly by squeezing: 5 lines over 120 characters, RECORD_CAPS depends on dict order, dict(reversed(...)).
N7. [minor] run_watch.py:120: no `cksum` on PATH: every tick fails, BLOCKED and "finished" never sent, the watcher never exits on DONE.
N8. [minor] at.py:1486 vs execute-plan/SKILL.md:183: with a live watcher lower caps are ignored; nothing says the owner must disarm then arm --watch to change caps, nor that this resets the count.
N9. [minor] at.py _run_guard_clear: disarm leaves `<session>.watch.state.<pid>` and `<session>.arm.<pid>` temp files of a killed writer.
N10. [minor] test_run_watch.py:202-207: test_finding4 failed once under load; timing-based.
## Status: DONE_WITH_CONCERNS
## Verdict: FAIL
## Findings: 0/1/9
