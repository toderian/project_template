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

## Gather Workbook Commands
- Command block from line 20 (bash):
  - `PYTHONDONTWRITEBYTECODE=1 python3 workbooks/model-eval-routing/scripts/run-small-eval.py \`
  - `  --fixture workbooks/model-eval-routing/samples/public-fixture.jsonl \`
  - `  --output .local/workbooks/model-eval-routing/small-eval.json`
- Command block from line 26 (bash):
  - `PYTHONDONTWRITEBYTECODE=1 python3 workbooks/model-eval-routing/scripts/summarize-failures.py \`
  - `  --input .local/workbooks/model-eval-routing/small-eval.json`

## Acceptance Criteria
- The evaluator command runs on the small public fixture.
- Failure cases are summarized without copying private examples.
- Any generated report that is kept outside Git is listed in `artifacts/README.md`.
- The task execution log records checks and remaining rollout decisions.

## Blockers And Risks
- Full private benchmark credentials are intentionally unavailable in this sample.

## Plan Next Slice
- Objective: complete `Phase 2 - run the small evaluator slice and compare failures` without pulling later phases forward
- Inputs: task file, related area docs, repo registry, workbook README, artifact registry if outputs are generated
- Stop point: task state updated, checks recorded, and the smallest reviewable slice complete

## Verify
- Run the narrowest deterministic checks named by the task or workbook
- Confirm generated, large, encrypted, external, or reproducible outputs are registered in artifacts/README.md when applicable
- Confirm `.creds/`, `.no-commit/`, raw private outputs, and absolute local paths are not copied into tracked artifacts

## Critique
- Challenge whether the selected phase is too broad, missing a baseline check, or depends on an unresolved blocker
- Escalate to a LangGraph-style workflow only if durable branching, retry, checkpoint/resume, or parallel lanes are now required

## Checkpoint
- Append an execution-log entry with actions, decisions, checks, and remaining work
- Commit only after the slice satisfies its acceptance criteria and required checks
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

## Gather Workbook Commands
- Command block from line 18 (bash):
  - `PYTHONDONTWRITEBYTECODE=1 python3 workbooks/debug-correction/scripts/reproduce-mismatch.py \`
  - `  --fixture workbooks/debug-correction/samples/sanitized-log.txt`
- Command block from line 23 (bash):
  - `PYTHONDONTWRITEBYTECODE=1 python3 workbooks/debug-correction/scripts/verify-correction.py \`
  - `  --fixture workbooks/debug-correction/samples/sanitized-log.txt`

## Acceptance Criteria
- The sanitized fixture reproduces the mismatch before the correction.
- The regression check fails before the fix and passes after the fix.
- The correction note identifies what remains out of scope.
- No raw private logs, prompts, or credentials are copied into tracked docs.

## Blockers And Risks
- The sanitized fixture may not cover all downstream log formats.

## Plan Next Slice
- Objective: complete `Phase 3 - verify the corrected output and document the known limitation` without pulling later phases forward
- Inputs: task file, related area docs, repo registry, workbook README, artifact registry if outputs are generated
- Stop point: task state updated, checks recorded, and the smallest reviewable slice complete

## Verify
- Run the narrowest deterministic checks named by the task or workbook
- Confirm generated, large, encrypted, external, or reproducible outputs are registered in artifacts/README.md when applicable
- Confirm `.creds/`, `.no-commit/`, raw private outputs, and absolute local paths are not copied into tracked artifacts

## Critique
- Challenge whether the selected phase is too broad, missing a baseline check, or depends on an unresolved blocker
- Escalate to a LangGraph-style workflow only if durable branching, retry, checkpoint/resume, or parallel lanes are now required

## Checkpoint
- Append an execution-log entry with actions, decisions, checks, and remaining work
- Commit only after the slice satisfies its acceptance criteria and required checks
```
