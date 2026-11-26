Peer: codex (model gpt-6-sol, effort default, cyber daybreak_blue), role plan-critic, 2026-11-26T07:22:53

## Status: DONE_WITH_CONCERNS

## Verdict: REVISE

### Scores

| Axis | Score | Delta | Evidence |
|---|---:|:---:|---|
| Assumption audit | 1 | — | Phase 3 promises archived `Note: parked:` lines, but `complete-task` copies only `Ruling:` and `Decision:` before deleting run state. |
| Scope creep | 3 | — | Phase 6 adds scripted lanes, but owner explicitly chose that scope in D4. |
| Existing solutions | 3 | — | `rg` found existing guard, driver, and skill-driven lane integration; plan builds on them. |
| Minimalism | 2 | — | Phases 1–6 add several modules plus one live-test file shared across lanes; file overlap is unresolved. |
| Uncertainty | 2 | — | Phase 0 probes harness behavior, but watchdog budget and restart ownership remain unspecified. |
| **Composite** | **2.2** | **—** | |

### Issues found

- **Evidence loss:** Phase 3 requires archived reports to include every parked question. [Completion flow](/home/vi/work/repos/project_template/plugins/agents-tasks/skills/complete-task/SKILL.md:99) does not preserve `Note: parked:` and deletes `_runs/` at line 112. No owner `Ruling:` authorizes losing it.
- **False parallel boundaries:** Phases 2 and 3 both edit `unattended-run/SKILL.md`; every phase extends `test-unattended-live.sh`. Phase 4 calls Phase 3’s report but says `After: 0, 2`. [Plan](/home/vi/work/repos/project_template/docs/specs/2026-11-26-unattended-run-hardening-plan.md:83).
- **Watchdog authorization:** `--budget-usd` is passed to each of up to four resumes; plan never defines a total spend cap or how watcher verifies task remains marked unattended. [Plan](/home/vi/work/repos/project_template/docs/specs/2026-11-26-unattended-run-hardening-plan.md:130).
- **Acceptance mismatches:** E5 expects an unspecified “restarted” notification; E6 allows two heartbeat intervals while acceptance requires one. E9 checks `state.md` after closeout, when completion deletes it. [Plan](/home/vi/work/repos/project_template/docs/specs/2026-11-26-unattended-run-hardening-plan.md:229).

### Required changes

1. Preserve parked questions and required phase evidence through closeout, or remove archived-report claims only with an owner `Ruling:` quoted from chat.
2. Correct `After:` and Order for shared files and Phase 4’s report dependency; isolate live scenarios by phase or serialize edits.
3. Define aggregate watchdog budget, restart authorization check, and atomic single-watcher ownership; test these limits.
4. Reconcile E5, E6, E9 with implementation steps and acceptance; require live evidence rather than treating CLI-missing `SKIP` as a pass.

## Status: DONE_WITH_CONCERNS
## Architecture verdict: REVISE
## Blocking findings: 4; evidence loss, phase overlap, watchdog limits, acceptance mismatches
## Required plan changes: preserve evidence; correct dependencies; bound restarts; reconcile live tests
