Peer: codex (model gpt-6-sol, effort default, cyber daybreak_blue), role reviewer, 2026-11-27T02:16:45

## Verdict: FAIL

1. [C] plugins/agents-core/lib/sup.py:305 — `land` can overwrite preserved evidence. If landing stops after moving an ignored file, then worker recreates that file before retry, `shutil.move` replaces existing `kept/<ID>` copy.
2. [I] plugins/agents-core/lib/sup_workers.py:830 — Existing hub file named by `local` cannot be linked. `src.mkdir()` raises `FileExistsError` for valid entry such as `data/cache.db`; `start-worker` refuses. Test covers missing file and existing directory, not existing file.
3. [I] plugins/agents-core/lib/sup_workers.py:285 — Invalid `Repos` values are silently discarded. With `Repos: other_repo`, `ready --pack` can print `ready` without required pack branch; worker then lacks intended sibling worktree.

## Evidence

- Reviewed `3a36951..HEAD` diff, plan acceptance, run state, landing cleanup, pack readiness, scheduling, and relevant tests. Findings above are unmet behavior; no existing ruling covers them.
- Landing guard checks added paths and untracked parents before squash merge (sup.py:255–267). Existing tests cover tracked directory replacement and ignored hub content.
- `Blocked by` scheduling and five minute pre-session retry are wired through `next_tasks` and watcher (sup_workers.py:337–369; sup_watch.py:280–307).

## Status: DONE_WITH_CONCERNS
## Summary: Three concrete defects remain; evidence can be overwritten on landing retry.
