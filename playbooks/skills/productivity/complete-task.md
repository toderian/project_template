# Complete Task

## Purpose

Close out a committed task safely. This workflow turns an active task into an archived `done` or
`cancelled` task only after acceptance checks, progress reconciliation, final execution notes,
completion harvest, generated ledgers, and strict validation all agree.

Use this workflow when work was completed but the task was never moved to `done`. Do not leave
implemented work sitting in `_todos/` just because the closeout step was missed; verify it, update the
task file, harvest the outcome, and archive it.

Follow `playbooks/conventions/todo-convention.md` for the task format and lifecycle.

## Prerequisites

The project must have `docs/tasks_manager/` initialized. If it is missing, run `/init` first.

## Process

### 1. Select the task

Accept either a task ID (`AUTH-001`, `T-004`) or a path under `docs/tasks_manager/_todos/`. Read the
task file. If it is already in `_todos_archived/`, report that it is already closed and stop.

### 2. Decide the terminal status

Use `done` when the acceptance criteria were met. Use `cancelled` when the task is intentionally not
being completed. Do not infer cancellation silently; the user or task history must make that decision
clear.

### 3. Verify acceptance, progress, and tests

For `done`:

- Check every acceptance criterion and phase item that must be complete.
- Resolve `Spec refs` and task-local spec/design sections. If the task implemented, partially
  implemented, superseded, or invalidated a durable spec, update that spec's status/evidence or record
  a follow-up when the update is outside closeout scope.
- Reconcile the task's phase/progress checkboxes with the actual completed work. Mark only items with
  evidence from code, docs, tests, commits, or execution logs.
- Run the related tests listed in the task, unless the task says `N/A - <reason>`.
- If a listed test cannot be run, record the exact command attempted and the reason.
- If the work appears complete in the repo but progress markers were stale, record that this is a
  closeout reconciliation in the execution log instead of pretending the progress was updated earlier.

For `cancelled`, record the reason and any useful partial validation instead of claiming acceptance.

### 4. Append the final execution log

Add a timestamped entry under `## Execution log` with:

- actions taken
- decisions made
- test or validation results
- final outcome

Keep the log append-only.

### 5. Fill the completion harvest

Complete every row under `## Completion harvest`:

```markdown
| Resource updates | docs/resources/... or None |
| Area updates | docs/areas/... or None |
| Follow-ups | I-NNN... or None |
| Notable decisions/deviations | short note or None, including spec status changes or skipped spec reconciliation |
```

Use explicit `None` rows when there is nothing to harvest. If a follow-up is needed, capture it with
`/capture-idea` first and list the `I-NNN`.

### 6. Write the completion summary

Replace the placeholder under `## Completion summary` with a short outcome summary and final validation
state. Include any tests that were skipped or could not be run.

### 7. Archive

Update metadata:

- `Status` to `done` or `cancelled`
- `Updated` to the current ISO 8601 datetime
- `Last executed` to the current ISO 8601 datetime if work or validation was performed

Move the file to `docs/tasks_manager/_todos_archived/` without changing its basename.

### 8. Sync and validate

Run:

```bash
_base/scripts/sync-todo-ledgers.sh
_base/scripts/sync-todo-ledgers.sh --check
```

If `--check` reports completion-harvest, status-directory, roadmap, or stale-ledger errors, fix them
before reporting success.

### 9. Optional downstream commit squash

For downstream repos, after the task is verified as `done`, archived, synced, and strictly validated,
you may squash the task's own execution and closeout commits into one final task commit. This is a
history-cleanup step, not a substitute for phase commits during execution.

Route the cleanup through `playbooks/skills/productivity/squash-workspace-commits.md`. That skill owns
the audit helper, safe auto-squash policy, pushed/shared-history refusal, unrelated-commit preservation
rules, backup-ref requirements, and final squashed commit-message requirements.

If the audit is blocked or uncertain, keep the phase commits and report that squash was skipped.

## Report

Return:

- task ID, terminal status, and archived file path
- acceptance/test result summary
- harvest rows that changed
- whether strict validation passed
- squash result, if attempted or skipped

## Quality bar

- Terminal tasks never remain in `_todos/`.
- Open or in-progress tasks never move to `_todos_archived/`.
- Archived tasks have explicit completion harvest rows and a non-empty completion summary.
- Linked durable specs are reconciled, or an explicit follow-up records why they were not updated.
- Generated ledgers and area blocks are synced and pass `_base/scripts/sync-todo-ledgers.sh --check`.
