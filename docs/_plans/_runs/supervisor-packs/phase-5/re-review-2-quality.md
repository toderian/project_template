Re-review round 2, phase 5 (quality). F1-F4 resolved; merges done.

## Status: DONE_WITH_CONCERNS
## Verdict: FAIL
## Findings: 4 (C:1 I:0 M:3)
N1. [C] plugins/agents-core/lib/sup.py:257-261 — a branch that turns a tracked directory into a file (`git rm -r data`, file `data`) passes the rule, and the landing deletes the hub's ignored content under it (`data/c.db`). Fix: when the hub path of an added `f` is a real directory, refuse if `git ls-files --others --ignored --exclude-standard -- f` lists anything.
N2. [M] scripts/tests/test_sup_land.py — the parent clause has no test (branch adds `sl/x`, hub holds ignored symlink `sl`).
N3. [M] sup.py:261 — the refusal names one remedy; add "or move the hub's copy away".
N4. [M] sup.py:260,:294 — one `git ls-tree` per added path that exists in the hub (9 s for 3000 files on a rerun); the kept-destination refusal does not say the commit is made.

Fix round 3 (orchestrator, at the cap): N1 fixed as named, with the test
test_a_branch_that_turns_a_tracked_directory_into_a_file_is_refused_while_the_hub_holds_ignored_files_in_it; N2 test
added (untracked link as a parent); N3 wording; N4 one `ls-tree -r` into a set, and the kept refusal says the commit
is made.
