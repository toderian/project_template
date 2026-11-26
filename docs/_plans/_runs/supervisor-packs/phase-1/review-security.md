## Status: DONE
## Verdict: PASS
## Findings: 5 (C:0 I:2 M:3)
1. [I] plugins/agents-core/lib/sup_workers.py:384 — the registry `Integration branch` cell reaches `git worktree add` unvalidated as the last argument; a cell starting with `-` is parsed as a git option. Fix: `_valid_branch` on the base.
2. [I] plugins/agents-core/lib/sup_workers.py:378 — `--branch sib=<existing branch>` attaches the pack worktree to any existing local branch, including the integration/default branch. Fix: refuse a branch equal to the registry's default or integration branch.
3. [M] plugins/agents-core/lib/sup_workers.py:255 — map paths are not required to be absolute, and no `--` separates options from the worktree path in lines 378/384.
4. [M] plugins/agents-core/lib/sup_workers.py:596 — `.local/repos.map` is written with `write_text` through any symlink at `.local` or `repos.map` in a reused task worktree.
5. [M] plugins/agents-core/lib/sup_guard.py:68 — `REPEATABLE` is global, so a `--branch` flag in any owner-defined table also becomes repeatable.

Passes: guard value class is a strict subset of SAFE_RUN; pack name and slug cannot carry `/` or `..`;
`_valid_branch` refuses `-x`, `@{`, `HEAD`, `a..b`; argv lists only; existing path refused unless same
common dir and branch; no delete site added; no secrets.
