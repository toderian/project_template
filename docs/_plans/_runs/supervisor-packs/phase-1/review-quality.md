## Status: DONE_WITH_CONCERNS
## Verdict: FAIL
## Findings: 9 (C:1 I:2 M:6)
1. [C] plugins/agents-core/lib/sup_workers.py:619-643 — a failed restart loses `sibling_base`: the old row is dropped under the first lock and the failure path drops the new one; the next start records a tip that already holds the worker's commits. Reproduced.
2. [I] plugins/agents-core/lib/sup_workers.py:380-384 — registry `Integration branch` cell reaches git unvalidated (`-` means `@{-1}`, `--detach` is an option). Reproduced.
3. [I] phase-1/report.md — does not exist; no Test plan; the restart branch (sup_workers.py:621) has no test.
4. [M] plugins/agents-core/lib/sup_workers.py:484 — `_refusal` does not know the repo rule: `start-worker RM-2` returns 0 while RM-1 runs on the same pack repo.
5. [M] plugins/agents-core/lib/sup_workers.py:263 — `_task_repos` copies the regex of task_run.py:909 and the glob of sup.py:357 and does not strip backticks.
6. [M] scripts/tests/test_sup_workers.py:404 — prompt sentence asserted on the constant and on argv.
7. [M] plugins/agents-core/lib/sup_workers.py:355 — `_git` raises `TimeoutExpired`/`OSError` uncaught in start-pack and start-worker.
8. [M] plugins/agents-core/lib/sup_workers.py:414 — `--branch sib=x --branch sib=y`: last wins silently.
9. [M] plugins/agents-core/lib/sup_workers.py:443-447 — pack read before the git work and re-read under the lock; a `pack` rewrite in between goes `running` without worktrees for its new branches.
