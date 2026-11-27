Final review, reviewer 1 (plan and run state; 44 mutations, 38 caught).

## Status: DONE_WITH_CONCERNS
## Verdict: FAIL
## Findings: 9 (C:1 I:1 M:7)
1. [C] sup_workers.py:830 — a `local` file entry that exists in the hub refuses every `start-worker` (`src.mkdir` raises FileExistsError). The skill's own example is `data/cache.db`.
2. [I] test_sup_workers.py:561 — the test "an archived blocker outside the pack does not block" passes with the behaviour removed.
3. [M] the worker row does not record `sibling_base` (plan phase 1); the landing range uses `pack["tips"]`. No ruling.
4. [M] sup_workers.py:797 — `_write_map` builds the pack worktree path by hand; `_pack_wt` exists.
5. [M] sup_workers.py:492, :461 — no test: "tip may move backwards" and "no recorded tip" guards.
6. [M] sup.py:248 — no test for "no range line when the task made no sibling commit".
7. [M] sup_workers.py:67 — the prompt sentence "You are on task/{task} ... on purpose" has no test.
8. [M] supervise/assets/supervisor.md:39,54 — the supervisor template does not show `--branch` or `ready --pack`.
9. [M] sup.py:356 `_resources` has one caller; `pack_problems` imports `sup_state as st` unused.
Acceptance: could pass with fake sessions for every criterion except `local` file entries (finding 1). A 1.17.0 profile and pack ran every command with exit 0.
