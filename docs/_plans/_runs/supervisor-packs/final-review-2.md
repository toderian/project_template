Final review, reviewer 2 (unanchored, code and tests only; real git probes).

## Status: DONE_WITH_CONCERNS
## Verdict: FAIL
## Findings: 10 (C:3 I:4 M:3)
1. [C] sup.py:258 — the landing guard reads only added paths: a modify/delete conflict on a branch based on an older default deletes the hub's ignored file (default untracked and ignored `conf.local`, the branch edits it; landing reports the conflict, `reset --hard` removes the hub's file).
2. [C] sup.py:258 — the guard checks the branch's path, not the path the merge writes: a directory rename on default (`git mv src lib`) lands the branch's `src/local.cfg` on the hub's ignored `lib/local.cfg`, which is deleted. A fix must check the merge result (`git merge-tree --write-tree`).
3. [C] sup.py:186,194 (older lines, shape not covered) — a branch that deletes a `.gitignore` line makes `git add -A` stage the hub's ignored files: `secrets.env` is committed; with a failing pre-commit hook `reset --hard` deletes it.
4. [I] sup_workers.py:347,362 — `next_tasks` calls `_held`/`_pack_repos` outside its `try`: one unreadable task file in a pack with branches stops every start of the profile, log only.
5. [I] sup_workers.py:247,254 — `_repos` lets `UnicodeDecodeError` escape: `at sup status` and `land --dry-run` print a traceback; other commands print the codec error without a file name.
6. [I] sup_workers.py:491, sup_digest.py:181 — a pack tip can become stale for ever (owner fixup commit above the tip; a worker amends a landed commit): `at sup done` exits 3 for ever, `close-pack` keeps the worktree; only editing the pack file helps.
7. [I] sup_digest.py `_waits` — status shows a reason only for `Blocked by`; a task held because another task holds its pack repo waits with no reason shown.
8. [M] sup_workers.py:801-802 — `_write_map` lets OSError escape (`.local` is a file).
9. [M] sup_workers.py:819 — `dst.resolve()` on a self-referencing link raises RuntimeError.
10. [M] pack records are read without shape checks: `branches` or `tips` as a list or string, or a missing `name`, give AttributeError/TypeError/KeyError.
Held: guard shapes with glob characters, nested `.gitignore`, nested git repository, file replacing a directory; four concurrent `start-pack`; the guard allow-list.
