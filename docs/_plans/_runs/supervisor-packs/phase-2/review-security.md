## Status: DONE_WITH_CONCERNS
## Verdict: FAIL
## Findings: 5 (C:0 I:2 M:3)
1. [I] plugins/agents-core/lib/sup_workers.py:557 — `close-pack` runs `git worktree remove` after a `git status --porcelain` clean check; ignored files in the pack worktree are deleted silently. Reproduced. Fix: keep the worktree and name the reason, or move the files to `kept/`.
2. [I] plugins/agents-core/lib/sup_digest.py:191 — registry `Integration branch` cell goes unvalidated into `git rev-list` argv (`--output=<path>..refs/heads/x` writes a file; reproduced) and into `at sup done` stdout the supervisor reads. Fix: `_valid_branch`, `refs/heads/` prefix.
3. [M] plugins/agents-core/lib/sup.py:238 — `at sup land <ID> --profile <other>` finds no pack: the dirty pack-worktree check and the tip advance are skipped (fail-safe later: `done` refuses).
4. [M] plugins/agents-core/lib/sup_workers.py:277 — the crash rerun reads `Repos` from the archived task file the worker wrote; a removed row leaves tips behind (`done` refuses).
5. [M] plugins/agents-core/lib/sup_digest.py:133 — `_branch_exists` passes `{branch}^{commit}` without `refs/heads/`.

Passes: digest section goes through `_word`/`_ptask`, count is int; commit body is slug, checked branch, SHAs,
one `-m` argv; map paths absolute; no `--force`, no branch delete; `_clean` fails closed; `kept_ignored`
skips exactly `.local/repos.map`.
