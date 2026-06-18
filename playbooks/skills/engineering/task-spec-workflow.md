# Task Spec Workflow

## Purpose

Normalize an existing task or a clear implementation idea into task-manager-native spec-driven work.
The output is a task file with enough planned intent, design shape, acceptance criteria, tests, and
spec references for `execute-plan` to implement without guessing.

This is the lightweight cousin of `spec-workflow`. Use this when the task manager should remain the
source of truth. Use `spec-workflow` only for heavyweight work that needs separate `specs/<slug>/`
artifacts and parallel implementer/reviewer loops.

## Source of Truth

Task files own executable work. Durable docs under `docs/resources/` own system knowledge and
cross-repo contracts.

Task-local sections:

- `### Specification` - planned behavior, non-goals, constraints, and open questions.
- `### Design` - planned approach, touched components, interface/data changes, tests, and rollout.

Task metadata:

- `Spec refs` - comma-separated references such as `self`, a PRD, `docs/resources/system-map.md`, an
  area summary, dependency graph, component context, or feature contract.

Task-local specs are planned intent until closeout reconciles the linked durable specs.

## Process

### 1. Resolve the Input

Accept any of:

- an existing `docs/tasks_manager/_todos/<TASK>.md`
- a task ID
- a clear idea that should become a task
- a PRD/plan/contract that should drive a task

If the input is a clear idea but no task exists, create one through `add-task` first. If the idea is
vague, capture it instead and stop; this workflow is for implementation-ready work.

### 2. Inspect Existing Context

Read:

- the task or source PRD/plan/contract
- `playbooks/conventions/todo-convention.md`
- relevant `docs/resources/system-map.md`, area summaries, dependency graphs, contracts, component
  contexts, and task history
- likely code/tests only as needed to ground the design

Classify each durable spec source by lifecycle status: `draft`, `accepted`,
`partially-implemented`, `implemented`, or `superseded`. Do not use planned specs as current-state
evidence.

### 3. Draft or Update the Task Spec

Update the task file, preserving existing useful content:

- add or update `Spec refs`; use `self` when task-local spec/design sections exist
- add `### Specification` when acceptance criteria alone do not preserve intent
- add `### Design` when the implementation approach needs agreement before code edits
- refine phases into committable steps
- ensure acceptance criteria are observable and testable
- list related tests, or `N/A - <reason>` when tests do not apply
- append an execution-log entry noting spec sources and lifecycle status

Do not implement code in this workflow. Stop before code edits.

### 4. Approval Boundary

Show a concise summary:

- task path and title
- spec sources and statuses
- notable non-goals and open questions
- phase list
- acceptance criteria and related tests

If open questions materially affect behavior or architecture, ask before marking the task ready for
execution. If all questions are non-blocking, record them under the task and report that `execute-plan`
can proceed.

### 5. Validate

Run:

```bash
_base/scripts/sync-todo-ledgers.sh
_base/scripts/sync-todo-ledgers.sh --check
_base/scripts/check-repos-config.sh
```

If `docs/tasks_manager/` is absent, run `init` before using this workflow.

## Quality Bar

- The task remains the source of truth for executable work.
- `Spec refs` names every durable spec the task must satisfy.
- Planned specs are not presented as implemented behavior.
- Acceptance criteria are testable and map to phases or related tests.
- Open questions that affect implementation are resolved or explicitly blocking.
- The workflow stops before code edits and hands off to `execute-plan`.
