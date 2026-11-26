Peer: codex (model gpt-6-sol, effort default, cyber daybreak_blue), role plan-critic, 2026-11-26T23:38:35

Status: BLOCKED

## Verdict: BLOCKED

### Scores

| Axis | Score | Delta | Evidence |
|---|---:|---:|---|
| Assumption audit | 1 | — | Phase 3 omits `task_lanes.py`, whose `PATH_RE` rejects `repo:path`; Phase 4 assumes profile `local` is retained, but `sup_tick.py:241` omits it. |
| Scope creep | 3 | — | Four phases address stated pack gaps; new preparation skill has a distinct task-editing role. |
| Existing solutions | 3 | — | Search found existing repo validation in `check_repos_config.sh`, blocker parsing in `task_run.py:1184`, and ledger conflict handling in `sup.py:33,174–182`. |
| Minimalism | 2 | — | Phase 1’s 150-line ceiling covers branch lifecycle, map parsing, scheduling, landing, and digest changes without a credible file-level shape. |
| Uncertainty | 1 | — | Phase 4 proposes discarding ledger changes and skipping `.local/` during ignored-file preservation; both can erase user content. |
| **Composite** | **2.0** | **—** | Two axes at 1 → BLOCKED. |

### Issues found

- **Ledger data loss:** `sup.py:33–36` treats only `_active.md` and `_done.md` as wholly generated. `sync_todo_ledgers.py:26–29` also edits marker blocks within area pages, whose surrounding text is hand-written. Phase 4’s blanket discard can erase those edits.
- **Ignored-file data loss:** `sup.py:262–271` moves ignored files before worktree removal. Skipping all `.local/` can discard unrelated files created there; linked paths also need collision and broken-link handling.
- **Phase 3 cannot stand alone:** `task_lanes.py:35–43` rejects colon-qualified `Files:` paths. Updating only supervisor readiness leaves execution’s file fence unable to parse the proposed format.
- **Existing-profile compatibility is unspecified:** `sup_state.py:182` defaults old packs to empty `branches`; `cmd_pack` currently replaces new packs without preserving them (`sup_workers.py:306–317`). `sup_tick.py:241` drops a proposed `local` key during init. State migration and restart behavior need defined checks.
- **Sibling evidence is weak:** `sup_digest.py:129–164` checks branch existence only. Phase 1 records a tip in hub commit text but specifies no check that later `done` still points to that tip or contains each task’s commits.
- **Resolved design conflicts with Phase 4:** D21 in the built session plan says lab scripts run only through `at sup op`; `sup_tick.py:441–462` enforces its allowlist and lease. Worker-run scripts change that rule without classifying D21 as implemented behavior being revised.

### Required changes

1. Limit ledger discard to wholly generated files; preserve hand-written area-page content and test conflicting edits.
2. Define exact linked paths, safe creation/removal, and preservation of every other ignored file.
3. Include `task_lanes.py` and its tests in Phase 3; specify parser behavior for repo-qualified paths.
4. Specify migration and restart checks for 1.17.0 profiles and packs, including `local` persistence.
5. Define branch-tip verification and recovery before `done` or worktree cleanup; revise Phase 1’s file-level shape and ceiling.
6. Mark D10/D21 promises as planned intent or implemented evidence, then explicitly resolve Phase 4’s change to D21.

## Status: BLOCKED
## Architecture verdict: BLOCKED
## Blocking findings: 6 — ledger loss; ignored-file loss; incompatible `Files:` parser; migration gap; unverified sibling commits; D21 conflict
## Required plan changes: Preserve user content; update shared parser; define migration and evidence checks; resolve D21; recalibrate Phase 1 shape.
