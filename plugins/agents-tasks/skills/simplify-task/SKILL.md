---
name: simplify-task
description: "Reduce an existing task file to the smallest plan that still delivers it: merge phases that share files and tests, cut or defer speculative checklist items and criteria, drop empty optional sections, then rewrite the task after showing the before/after. Use when the user says \"simplify task\", \"this task is too big\", \"descope\", or a task fails the small-mode gate of execute-plan by a small margin."
disable-model-invocation: true
metadata:
  pack: task-management
---

# Simplify Task

## Purpose

Take a task that already exists in `docs/tasks_manager/_todos/` and make it the smallest plan that
still satisfies its brief: fewer phases, fewer criteria, no placeholder sections. The task file is
the plan; this is the planning-time counterpart of `agents-core:simplicity-review` (which reviews
code). It rewrites the file only after the user has seen the diff.

Prerequisite: the task exists and is `open` or `in_progress`. An archived task is never simplified.

## Process

### 1. Read the task and its history

Read the task file and `git log --follow --oneline -- <task file>`, so later drift is visible and a
criterion that was added deliberately after a review is not mistaken for padding. Read code only
where a phase item names a file and the item's necessity depends on what is there. Do not read
other tasks, the roadmap, or the knowledge base; scope is this file.

### 2. Classify every item

Build one table over every phase checklist item and every acceptance criterion:

| Item | Action | Reason | Trigger (defer only) |
|------|--------|--------|----------------------|

Actions and the rule that assigns them, in order:

1. **cut** — the item exists to satisfy a template, not the brief: a "current-state review" phase,
   a criterion that restates another, a checklist item with no observable outcome, an optional
   section still holding placeholder text.
2. **defer** — the item is real work the brief does not require now (a second format, a config
   flag nobody set, a generalisation "for later"). Name the trigger that would make it necessary.
   It is not lost: step 5 records it under `### Follow-ups` (an `I-NNN` capture when the repo
   uses the inbox).
3. **merge** — two phases that touch the same files and are proven by the same tests are one
   phase; a criterion with no phase delivering it is attached to the phase that does, or a
   phase item with no criterion proving it gets one (or is cut).
4. **keep** — everything the brief states, the user asked for, or a `Ruling:` line in
   `_runs/<ID>/state.md` decided.

Guard: an item the brief states explicitly, or that the user asked for in the current
conversation, may only be `keep` or `merge`. Never touch the execution log, the metadata table
(except `Updated`), or a phase already ticked.

### 3. Propose the shape

Aim for one phase; two when the second is separately committable and reviewable; three or more
only when the brief describes independent deliverables. If the result still has ≥ 3 phases or ~10+
files in scope, say so: it belongs on the large rung of `agents-core:execute-plan`, and that is a
legitimate answer.

Show, in this order:

- counts before → after: phases, checklist items, acceptance criteria
- the table from step 2 (every row, `keep` rows last)
- the proposed task file diff (`diff -u` style, phases and criteria sections only)

Then **stop for approval**. If a cut needs a decision only the user can make (two criteria that
contradict, a deferred item the user may still want now), run `agents-core:grilling` on those
rows only; do not grill the whole task.

### 4. Nothing to cut

If every row is `keep`, reply `Lean already.` with the counts and stop. Do not manufacture cuts.

### 5. Rewrite on approval

1. Rewrite `### Phases`, `### Acceptance criteria` and (when items were deferred)
   `### Follow-ups`; remove optional sections that were still placeholders.
2. Update `Updated`; append one execution-log entry: `Simplified: N→M phases, K items cut, J
   deferred (see Follow-ups)` — create the `## Execution log` section if the task has none.
3. If `_runs/<ID>/state.md` exists, its phase rows no longer match: leave a `Note:` line there
   naming this simplification and tell the user to re-run `at task run-state init <ID> --force`
   before executing.
4. `at ledger sync && at ledger check`.

Report: the counts, the file path, the follow-ups captured, and whether the task now fits the
small rung.

## Quality bar

- Every `cut` and `defer` has a reason a later reader can check against the brief.
- Nothing the brief or the user asked for was removed; deferred work is recorded, never dropped.
- The file was rewritten only after the diff was shown and approved.
- `at ledger check` passes; the execution log records the simplification in one entry.
