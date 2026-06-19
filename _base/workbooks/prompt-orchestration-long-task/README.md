# Prompt Orchestration Long Task

## Purpose

This workbook helps agents and humans plan the next reviewable slice of a long-running task from
existing repo artifacts. It reads a task file and, optionally, a related workbook README, then prints a
deterministic brief for intake, current-state review, task classification, next phase selection,
workbook commands, verification, critique, and checkpointing.

It is intentionally not a LangChain or LangGraph application template. It is a small, vendor-neutral
planning workbook. Downstream projects can adopt LangGraph later when durable graph state, branching,
checkpoint/resume, retries, human interrupts, or parallel lanes become real requirements.

## Depends on

None.

## Contents

- `scripts/plan_next_slice.py` - read-only standard-library helper that summarizes the next task slice.
- `samples/RMM-010-model-eval-feature.md` - sanitized synthetic feature/eval task inspired by a
  RedMesh-style model workflow.
- `samples/EGM-013-debug-correction.md` - sanitized synthetic debug correction task inspired by a
  RedMesh-style failure-correction workflow.
- `samples/model-eval-workbook.README.md` - sanitized related-workbook README with runnable command
  examples for the feature/eval sample.
- `samples/debug-correction-workbook.README.md` - sanitized related-workbook README with runnable
  command examples for the debug sample.
- `outputs/sample-output.md` - expected output examples showing the workbook loop.

## How to run/use

Run from the repository root after this workbook is copied or seeded into `workbooks/`:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 workbooks/prompt-orchestration-long-task/scripts/plan_next_slice.py \
  --task docs/tasks_manager/_todos/<TASK>.md \
  --workbook workbooks/<related-workbook>/README.md
```

To verify the seeded samples from the template checkout:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 _base/workbooks/prompt-orchestration-long-task/scripts/plan_next_slice.py \
  --task _base/workbooks/prompt-orchestration-long-task/samples/RMM-010-model-eval-feature.md \
  --workbook _base/workbooks/prompt-orchestration-long-task/samples/model-eval-workbook.README.md

PYTHONDONTWRITEBYTECODE=1 python3 _base/workbooks/prompt-orchestration-long-task/scripts/plan_next_slice.py \
  --task _base/workbooks/prompt-orchestration-long-task/samples/EGM-013-debug-correction.md \
  --workbook _base/workbooks/prompt-orchestration-long-task/samples/debug-correction-workbook.README.md
```

Arguments:

- `--task` is required and points to a Markdown task file.
- `--workbook` is optional and points to a related workbook `README.md`.
- `--max-log-lines` is optional and limits how many execution-log bullets are echoed.

The script reads files and prints to stdout only. It does not call a model, access the network, write
files, inspect credentials, or execute workbook commands.

Success criteria:

- the selected next phase is the first unchecked phase-like checkbox, or the task is reported as having
  no open phase checkbox
- commands are copied only from fenced shell/bash/text blocks in the related workbook README
- blockers, acceptance criteria, and recent execution-log entries are surfaced for human review
- output is deterministic for the same inputs

Cleanup: none. Set `PYTHONDONTWRITEBYTECODE=1` if you want to avoid local `__pycache__/` creation.

## Methodology

The workbook follows the prompt-orchestration convention:

```text
intake -> current-state review -> classify task -> select next phase -> gather workbook commands
       -> plan next slice -> verify -> critique -> checkpoint
```

The script is deliberately heuristic. It is meant to reduce context loss before a long-task session,
not to replace task ownership, planning judgment, `/execute-plan`, or `/complete-task`.

Task classification uses the task filename prefix as a routing hint:

- `F-*` feature/product slices
- `D-*` defects or diagnosis
- `C-*` chores/conventions/infrastructure
- `R-*` research/report/resource work
- area prefixes such as `RMM-*`, `EGM-*`, `RM-*`, and `EG-*` for area-scoped downstream work
- `T-*` global template or cross-area work

LangGraph adoption should remain downstream-specific. Add it only when the plain workbook loop cannot
represent required state transitions, resumability, retries, human interrupts, or parallel lanes.
