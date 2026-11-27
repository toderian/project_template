Re-review round 1, phase 2, security. 1: resolved. 2: resolved. 6: resolved.

## Status: DONE
## Verdict: PASS
## Findings: 3 (C:0 I:0 M:3)
1. [M] plugins/agents-core/lib/sup_workers.py:422 — a profile with no `hub` key in `config.json` is matched only by name, so `land` without `--profile` still passes its pack.
2. [M] plugins/agents-core/lib/sup_workers.py:423 — a non-string `hub` in any profile's `config.json` raises `TypeError`: traceback, every landing stops.
3. [M] plugins/agents-core/lib/sup.py:270 — `--grep=Archive: refs/archive/task/RM-1` is a substring match: it also finds the commit of `RM-10`.
A task title cannot forge a range line (subject is one line whose first token ends in `:`; body lines are tool-built).
