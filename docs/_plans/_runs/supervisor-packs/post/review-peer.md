Peer: codex (model gpt-6-sol, effort default, cyber daybreak_blue), role reviewer, 2026-11-27T06:13:15

## Status: DONE_WITH_CONCERNS
## Verdict: FAIL
## Findings: 2 (C:1 I:1 M:0)

1. [C] `plugins/agents-core/lib/sup.py:272` — Scratch repo: branch added `src/local.cfg`; hub renamed `src/` to `lib/` and held ignored `lib/local.cfg` containing `OWNER PRIVATE`. Simulating Git without `merge-tree --write-tree` made `sup land TST-001` refuse on conflict **after deleting hub file**. Landing must refuse before touching checkout when merge result cannot be computed.
2. [I] `plugins/agents-core/lib/sup.py:475` — Scratch repo: `other` existed in `.local/repos.map` and pack branch, but not repo registry. Task’s `Repos: other` returned `ready` (exit 0). It should produce registry problem line.

## Evidence

- Landing: current Git’s preflight named conflict without checkout changes; simulated unavailable merge-tree triggered branch-diff fallback, then squash/reset lost ignored file.
- Registry: reproduced map-only entry using pack readiness fixture. Existing test covers wholly unknown slug, not map-only slug.
- Other claims: inspected worker start/wake, unreadable-file handling, accept-tip guards, digest and slug changes. `test_sup_workers.py`: 47 passed. `test_sup_land.py` exceeded 110-second limit.
- Consequences 1: changed land path called through `sup land`; fallback reaches `squash_and_commit`.
- Consequences 2: `merge_result` returns `None` on command failure; caller treats that as permission to use branch diff.
- Consequences 3: failed squash invokes hard reset, which cannot restore deleted ignored content.
- Consequences 4: rename on default moves branch addition to path branch diff does not name.
- Consequences 5: command logs conflict refusal after loss; ignored file has no Git recovery record.
- Consequences 6: existing landing test fails for data-loss class only when merge-tree remains available; map-only registry input is untested.
