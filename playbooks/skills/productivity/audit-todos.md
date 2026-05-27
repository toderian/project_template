# Audit Todos

## Purpose

Audit active task files against the current repository state so stale backlog work can be handled
deliberately. Use this as a periodic active-task health check when tasks may be outdated, already
completed, obsolete, duplicated, or closeable with a follow-up.

The default output is a Markdown report with recommendations and evidence. This skill is report-only
unless the user explicitly chooses a follow-up workflow.

## Default scope and safety

Start from active tasks only:

- `docs/tasks_manager/_todos/`

Use the rest of the task system as context, not as the primary audit target:

- `docs/tasks_manager/_roadmap.md`
- `docs/tasks_manager/_active.md`
- `docs/tasks_manager/_done.md`
- `docs/areas/`
- `docs/resources/`
- `docs/archive/`
- `docs/tasks_manager/_todos_archived/` only for duplicate, superseded, or already-finished evidence

Do not edit task files, archive tasks, capture follow-ups, reorder the roadmap, or regenerate ledgers
by default. If the audit finds work to close or change, recommend the existing workflow:

- `/complete-task` for done or cancelled closeout
- `/capture-idea` or `/add-task` for follow-ups
- `/roadmap` for sequencing cleanup

Evidence controls the recommendation. Age alone never justifies closing, cancelling, or changing a
task. A task that is old but still valid is `keep`.

## Process

### 1. Frame the audit

Confirm the audit target from the user's prompt. With no narrower target, audit every active task under
`docs/tasks_manager/_todos/`. If `docs/tasks_manager/` does not exist, report that the task system is
not initialized and stop.

Run `git status --short` before inspecting so the report can mention whether uncommitted work might
affect the current-state read. Do not modify the worktree during the audit.

### 2. Build the task inventory

For each active task, read:

- metadata table
- title and brief
- phases
- acceptance criteria
- related tests
- follow-ups
- execution log
- completion harvest and summary placeholders, if present

Also read the roadmap, active/done ledgers, relevant area pages, and resource docs. If generated views
look stale, run `_base/scripts/sync-todo-ledgers.sh --check` when available because it is read-only; otherwise
record the stale-view concern in the report.

### 3. Check repo evidence

For every task that receives a meaningful recommendation, check the current repo state. Derive search
terms from the task ID, title, brief, phases, acceptance criteria, related tests, follow-ups, and domain
terms. Inspect likely code, tests, docs, scripts, config, and recent commits as needed.

Use structured repo evidence where possible:

- existing files from `rg --files`
- exact matches from `rg -n`
- related tests listed by the task
- docs/resources and area pages that describe the current architecture
- archived task completion harvests or summaries that may supersede the active task
- git history for likely implementation paths, when current files alone do not explain the state

Do not infer "done" or "obsolete" from missing search results. If no matching code or test evidence is
found, cite the searches and classify the task as `keep` or `needs-user-decision` depending on whether
the task is still understandable and actionable.

For documentation-only or research-only tasks, still search the repo for implementation surfaces. If
there is genuinely no code surface, say that explicitly and base the recommendation on docs/resources,
task history, and related artifacts.

### 4. Classify each task

Use exactly one primary classification per task:

- `keep` - the task still appears valid, actionable, and not contradicted by current code/tests/docs.
- `needs-update` - the task is still worth doing, but its brief, phases, acceptance criteria, related
  tests, area, dependencies, or roadmap placement no longer match the repo.
- `appears-done` - current code/tests/docs satisfy the task's acceptance criteria closely enough that
  `/complete-task` should verify and close it.
- `cancel-or-close` - evidence shows the task is obsolete, superseded, duplicated by another task, no
  longer in scope, or should be intentionally cancelled; require user confirmation or `/complete-task`
  cancellation.
- `split-follow-up` - the original task can close or shrink, but a distinct remaining idea should be
  captured or promoted separately.
- `needs-user-decision` - evidence is conflicting, strategically ambiguous, blocked on product choice,
  or too weak for a confident recommendation.

Prefer the most conservative classification that fits the evidence. If two recommendations are close,
choose `needs-user-decision` and show the conflict.

### 5. Write the report

Group the report by recommendation, with higher-action categories first:

1. `appears-done`
2. `cancel-or-close`
3. `split-follow-up`
4. `needs-update`
5. `needs-user-decision`
6. `keep`

Use this structure:

```markdown
# Audit Todos Report

Scope: <all active tasks | task IDs | area>
Worktree: <clean | dirty summary>
Task sources read: <paths>
Repo checks run: <commands or search patterns>

## Summary

| Recommendation | Count | Task IDs |
|----------------|-------|----------|
| appears-done | 0 | - |
| cancel-or-close | 0 | - |
| split-follow-up | 0 | - |
| needs-update | 0 | - |
| needs-user-decision | 0 | - |
| keep | 0 | - |

## <Recommendation>

### <TASK-ID> - <Task title>

Recommendation: `<classification>`
Confidence: <high | medium | low>
Evidence:
- Task evidence: <task fields or execution log facts with file paths>
- Repo evidence: <code/test/doc facts with file paths and line numbers where possible>
- Related checks: <commands, test files, or searches inspected>
Why this classification fits:
- <short explanation>
Next action:
- <workflow command or "none">
```

Do not hide weak evidence. If the recommendation depends on a negative search result, include the
search terms and explain what was not found.

## Scenario guide

- Active task appears implemented in code/tests: classify `appears-done` only when repo evidence maps
  to the task's acceptance criteria; recommend `/complete-task`.
- Active task is obsolete or superseded: classify `cancel-or-close` only with concrete current-state
  evidence such as a replacement task, archived completion, removed subsystem, or documented decision.
- Active task duplicates another task: classify `cancel-or-close` or `needs-user-decision`, cite the
  canonical task candidate, and do not merge or cancel without the user's choice.
- Task remains open but needs updated criteria/tests: classify `needs-update`, cite the mismatch, and
  recommend the exact task-field changes for a separate user-approved maintenance pass; use `/roadmap`
  only for sequencing cleanup and `/capture-idea` or `/add-task` only for distinct new work.
- Task should close with a follow-up: classify `split-follow-up`, recommend `/complete-task` for the
  satisfied core and `/capture-idea` or `/add-task` for the remaining distinct work.
- No matching code evidence found: do not treat absence as completion or cancellation; classify `keep`
  when the task is still coherent, otherwise `needs-user-decision`.

## Quality bar

- Every task recommendation, including `keep`, cites task evidence and repo evidence or an explicit
  search-limited note.
- Every `appears-done` recommendation maps current code/tests/docs to acceptance criteria.
- Every `cancel-or-close` recommendation explains why active work should not continue.
- Every `split-follow-up` recommendation separates closeout work from the follow-up.
- Recommended mutations are delegated to `/complete-task`, `/capture-idea`, `/add-task`, or `/roadmap`.
- The audit itself leaves the worktree unchanged.
