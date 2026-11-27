## Status: DONE_WITH_CONCERNS
## Verdict: FAIL
## Findings: 8 (C:1 I:4 M:3)
1. [C] plugins/agents-core/lib/sup_workers.py:556 — `close-pack` deletes ignored files: "clean" is `git status --porcelain`, then `git worktree remove` drops `.no-commit/` silently. Reproduced.
2. [I] plugins/agents-core/lib/sup.py:234-237 — `at sup land <ID>` with no profile skips the pack (dirty worktree lands, no range, tips old, rerun impossible).
3. [I] plugins/agents-core/lib/sup.py:268-269 — a rerun advances tips to the current branch tip, not the tip in the hub commit body; after a crash past the archive ref a hand rerun of `land T1` sets the tip mid-T2. Reproduced.
4. [I] plugins/agents-core/lib/sup_digest.py:132,247,430 — a relative path in `.local/repos.map` gives a `Refused` traceback in `status` and `done`.
5. [I] plugins/agents-core/lib/sup_tick.py:364,431 — the same `Refused` reaches the tick and chat through `digest()`.
6. [M] plugins/agents-core/lib/sup_workers.py:547 — `close-pack` writes `closed` before the map read; a `Refused` exits 3 with the pack already closed.
7. [M] scripts/tests/test_sup_land.py:388-389 — `kept/` assertions repeat test_sup_flow.py:334-335; dirty refusal in both.
8. [M] scripts/tests/test_sup_digest.py:275 — the status test never puts a real task id in the row.
