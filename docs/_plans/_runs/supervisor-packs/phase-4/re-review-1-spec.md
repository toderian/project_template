Re-review round 1, phase 4, spec. 2: open (new defect, finding 1). 5: open (no reason given). 9, 13, 14, 16, 17: resolved. 15: half (line 68 unwrapped). 18: open (finding 2).

## Status: DONE_WITH_CONCERNS
## Verdict: FAIL
## Findings: 4 (C:0 I:2 M:2)
1. [I] plugins/agents-core/lib/sup.py:427 — every registry slug is checked even when the hub's own slug cannot be determined: registry row `hub`, no map line for the hub, task `Repos: hub` is refused, and `--branch hub=x` cannot repair it. A 1.17.0 pack is refused. No test.
2. [M] plugins/agents-tasks/skills/prepare-pack/SKILL.md:35 — "Each registry slug needs a `--branch` ... with or without a line in `.local/repos.map`" is false: the hub's slug needs none, and a slug without a map line cannot get a branch. True: every sibling repo in `Repos` needs a map line and a `--branch`.
3. [I] size-fix-1.md — lib net 101 against 80, no stated reason.
4. [M] plugins/agents-tasks/skills/prepare-pack/SKILL.md:68 — 185-character line.
