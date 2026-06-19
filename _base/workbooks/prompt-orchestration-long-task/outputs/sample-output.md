# Sample Output

The exact line numbers below may change if the sample task files are edited. The flow should remain:
intake, current-state review, classify task, select next phase, gather workbook commands, plan next
slice, verify, critique, checkpoint.

## Model/Eval Feature Sample

```text
# Long-Task Next Slice Brief

## Intake
- Task: RMM-010 Model Evaluation Routing
- Task path: _base/workbooks/prompt-orchestration-long-task/samples/RMM-010-model-eval-feature.md
- Workbook: Model Eval Routing Workbook
- Workbook path: _base/workbooks/prompt-orchestration-long-task/samples/model-eval-workbook.README.md

## Current-State Review
- Completed checkboxes: 1
- Open checkboxes: 2
- Recent execution log:
  - 2026-06-18 - Collected synthetic baseline examples and confirmed no private task text is needed.
  - 2026-06-19 - Ready to run the small evaluator slice from the related workbook.

## Classify Task
- Classification: area-scoped task (RMM)
- Routing note: Read area docs, repo registry rows, contracts, runbooks, and workbook state.

## Select Next Phase
- Next phase: line 13: Phase 2 - run the small evaluator slice and compare failures
```

## Debug Correction Sample

```text
# Long-Task Next Slice Brief

## Intake
- Task: EGM-013 Debug Correction Loop
- Task path: _base/workbooks/prompt-orchestration-long-task/samples/EGM-013-debug-correction.md
- Workbook: Debug Correction Workbook
- Workbook path: _base/workbooks/prompt-orchestration-long-task/samples/debug-correction-workbook.README.md

## Current-State Review
- Completed checkboxes: 2
- Open checkboxes: 1
- Recent execution log:
  - 2026-06-17 - Reproduced the mismatch with a synthetic fixture.
  - 2026-06-18 - Added the regression case and confirmed the correction rule is narrow.

## Classify Task
- Classification: area-scoped task (EGM)
- Routing note: Read area docs, repo registry rows, contracts, runbooks, and workbook state.

## Select Next Phase
- Next phase: line 14: Phase 3 - verify the corrected output and document the known limitation
```
