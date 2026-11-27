Re-review round 1, phase 5 (quality, with spec and security items). 2-5, 7-10: resolved. 1: open (F1, F2). 6: open (F3).

## Status: DONE_WITH_CONCERNS
## Verdict: FAIL
## Findings: 4 (C:1 I:2 M:1)
F1. [C] plugins/agents-core/lib/sup.py:238 — guard (b) runs only with a profile: `at sup land T-1` by hand without `--profile` lands a branch that tracks the link (the worker changed the branch `.gitignore` to `shared/` and committed); `hub/shared` becomes a link to itself, `data.txt` gone.
F2. [I] sup.py:241-243 — guard (b) misses a branch that tracks a parent of an entry (`lab` as a file or link, entry `lab/results/`): hub `lab/results/r.txt` gone.
F3. [I] sup.py:288-290 — the kept-destination check passes when the destination itself is a symlink to a directory: the move writes into it.
F4. [M] plugins/agents-core/lib/sup_workers.py:826 — any non-zero `check-ignore` exit is reported as "git does not ignore".
Mergeable: `current_profile` computed twice in `cmd_land`; `_link_local` runs the hub check-ignore and then the worktree one.
