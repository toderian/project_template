Reviewer: agents-core:reviewer (landing safety), 2026-11-27. Findings as reported; the evidence section is shortened.

## Status: DONE_WITH_CONCERNS
## Verdict: FAIL
## Findings: 6 (C:1 I:3 M:2)

On git 2.38+ no probe made a landing delete, overwrite or commit an ignored hub file. The failures are the old-git
fallback, a race window before `git add -A`, and `assume-unchanged` edits.

1. [C] `sup.py:203-208, 272-277, 199` — the fallback (no `merge-tree --write-tree`, git < 2.38) deletes ignored hub files.
   Repro a: default renames `old/` to `new/`, branch adds `old/f.bin`, hub holds ignored `new/f.bin`: land refuses on the
   conflict, exit 3, and `new/f.bin` is gone. Repro b: default deletes `f.bin` and ignores `*.bin`, hub recreates it, branch
   modifies it: same. Cause: the guard reads added paths of `default...branch` only; the merge writes the conflict path and
   `reset --hard` removes it.
2. [I] `sup.py:186-191, 199` — a file that appears in the hub after the `loose` check and before `git add -A` is committed,
   or deleted when the commit fails. Should: stage only the merge result and the generated ledger paths.
3. [I] `sup.py:94, 199` — a hub file marked `git update-index --assume-unchanged` with a local edit is lost on any failed
   landing: `is_dirty` reports clean, then `reset --hard HEAD` rewrites it. `--skip-worktree` edits survived.
4. [I] `sup.py:51-52, 149` — a non-UTF-8 ignored filename in the task worktree crashes land with a `UnicodeDecodeError`
   traceback after the commit is made; every rerun crashes the same way. A non-UTF-8 path on the branch crashes before
   the checkout is touched.
5. [M] `sup.py:272-286` — a cleanup-only rerun still runs the added-path guard and can refuse with "landing would replace
   it" though no merge would run.
6. [M] `sup.py:325` — `kept/<ID>/agen` kept as a file earlier, then the worktree holds ignored `agen/b`: every rerun fails
   with `[Errno 17] File exists`; nothing is lost, no way out is named.

## Evidence (shortened)
- Held on git 2.43: ignore sources, shape swaps, links and nested repos, renames, `--into`, generated conflicts together
  with held paths, newline in a path, `status.showUntrackedFiles=no`; valid landings accepted; hook failure, ledger-check
  failure and a held lease left the hub intact and the rerun landed.
- Probes: scratchpad `post-landing/` (`h.py`, `p1.py`…`p4.py`, `p5_item2.py`, `fakegit/git`).
