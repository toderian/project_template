# EGM-013 Debug Correction Loop

| Field | Value |
| --- | --- |
| Status | in-progress |
| Area | EGM |
| Related workbook | `workbooks/debug-correction/README.md` |
| Updated | 2026-06-19 |

## Phases

- [x] Phase 1 - reproduce the parser mismatch on a sanitized fixture
- [x] Phase 2 - isolate the correction rule and add a regression case
- [ ] Phase 3 - verify the corrected output and document the known limitation

## Acceptance Criteria

- The sanitized fixture reproduces the mismatch before the correction.
- The regression check fails before the fix and passes after the fix.
- The correction note identifies what remains out of scope.
- No raw private logs, prompts, or credentials are copied into tracked docs.

## Risks

- The sanitized fixture may not cover all downstream log formats.

## Execution Log

- 2026-06-17 - Reproduced the mismatch with a synthetic fixture.
- 2026-06-18 - Added the regression case and confirmed the correction rule is narrow.
