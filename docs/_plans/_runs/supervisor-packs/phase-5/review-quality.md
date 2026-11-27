Stage: quality, phase 5.

## Status: DONE_WITH_CONCERNS
## Verdict: FAIL
## Findings: 6 (C:1 I:2 M:3)
1. [C] plugins/agents-core/lib/sup_workers.py:806 (`_link_local`) with sup_state.py:170 — hub content deleted at landing. The validator runs `git check-ignore` only in the hub. When the task branch's `.gitignore` differs (branch has `shared/`, hub now `shared`; or the branch predates the ignore line) the link is untracked in the worktree, a phase commit tracks it, and the squash-merge replaces the hub's ignored directory with that symlink: `hub/shared -> hub/shared`, `data.txt` gone, hub commit tracks `120000 shared`. Probed. Fix: before `symlink_to`, require `git -C <worktree> check-ignore -q -- <entry without />`, else Refused naming the entry; add the test.
2. [I] scripts/tests/test_sup_land.py:102 — the test does not pin the skip rule: a mutant that skips every symlink passes. Missing: a link retargeted elsewhere, or an entry dropped from the profile, lands in `kept/<ID>`.
3. [I] plugins/agents-core/lib/sup.py:279-283 — `local` is read and validated after the squash commit. Read the list with the other pre-checks before `squash_and_commit`; drop the try/except and its message.
4. [M] sup_workers.py:819,826 — OSError from mkdir/symlink_to is not caught: traceback.
5. [M] sup_state.py:160 — nested entries (`a/`, `a/b/`) pass init then refuse every start; `check-ignore` exit 128 is reported as "is not ignored"; `:/a` passes as pathspec magic.
6. [M] sup_state.py:181 — a bad profile.json surfaces the raw JSON error without the file name.
