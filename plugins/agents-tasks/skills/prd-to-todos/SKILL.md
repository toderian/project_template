---
name: prd-to-todos
description: "Extract actionable tasks from a PRD and create area-prefixed task files. Use when the user wants to convert a PRD into trackable tasks in docs/tasks_manager/_todos/."
metadata:
  source: playbooks/skills/productivity/prd-to-todos.md
  pack: task-management
---

# PRD to Tasks

## Purpose

Extract actionable tasks from an existing PRD and create task files following the standard convention.

## Prerequisites

The project must have `docs/tasks_manager/` initialized. If it does not exist, run `/init` first.

## Process

### 1. Locate the PRD

Ask the user for the PRD source. It can be:

- A GitHub issue number — fetch with `gh issue view <number>`
- A file path — read the file
- Already in the conversation context

### 2. Extract vertical slices

Break the PRD into actionable items. Prefer vertical slices (end-to-end through all layers) over
horizontal slices (one layer at a time) — see
[the `prd-to-plan` skill (references/vertical-slicing.md)](../prd-to-plan/references/vertical-slicing.md) for the shared
tracer-bullet framing `prd-to-plan` and `agents-extras:prd-to-issues` also use.

Each item should be:

- **Atomic**: one clear deliverable
- **Independently completable**: can be worked on without finishing other items first (note dependencies if they exist)
- **Verifiable**: has concrete acceptance criteria

### 3. Break each slice into phases

For each vertical slice, identify logical phases — committable steps that build on each other. Think: "Where are the natural commit points?"

Each phase should:

- Produce a working, committable state
- Be small enough to reason about
- Build on the previous phase

### 4. Check for existing work

Before asking the user to approve task creation, run the discovery scan from
the `task-ledger` skill §"Discovery gate" against the proposed slices (inbox
+ archived, active + archived tasks, roadmap/ledgers/area pages, `docs/resources/` + `docs/archive/`
and their area docs, and likely code/tests).

If a slice is already captured, tracked, implemented, obsolete, or related-but-distinct, show the
evidence with the proposed task list. Ask whether to skip it, append detail to the existing item, link
it from the new task, or keep it as a distinct task. Do not create duplicate committed work silently.

### 5. Quiz the user

Present the proposed tasks as a numbered list. For each:

- **Title**: short descriptive name
- **Area / prefix**: existing area row from `_areas.md`, or a proposed new area
- **Repos**: if `.config/repos.project.md` exists, comma-separated repo slugs when inferable, or omitted when not
  clear
- **Autonomy**: optional `L0`-`L3` only when the PRD/user explicitly requests a loop level or the task
  should be stricter than the repo default/max
- **Spec refs**: the PRD path/issue, `self`, or durable docs/contracts each task must satisfy
- **Type**: `F` / `D` / `C` / `R`
- **Priority**: high / medium / low
- **Dates**: optional `Target date` / `Deadline` only when the PRD or user states task-specific dates;
  otherwise omit
- **Roadmap milestone**: optional goal-level `target` / `deadline` date only when the user wants the
  PRD scheduled
- **Phases**: list of committable steps
- **Acceptance criteria**: overall criteria for the task to be done
- **Related tests**: known test files that will be affected or created, or `N/A - <reason>`
- **Blocked by**: which other tasks must complete first (if any)

Ask the user:

- Is the granularity right?
- Do the phases make sense as commit points?
- Should any items be merged or split?
- Are any items missing?

Iterate until approved.

### 6. Create task files

For each approved slice, create the task exactly as `add-task` does — its steps 3–6 are the canonical
ritual for area/prefix, type, priority, the optional `Repos`/`Autonomy`/`Spec refs`/date metadata, the
full `todo-convention.md` file shape, `at reserve` reservation, and the
`at ledger sync`/`at ledger check`/`at repos-check` step. Do not restate those field rules
here. PRD-specific overrides:

- set `Source: prd-to-todos` and `Source ref` to the PRD path/issue; set `Spec refs` to the PRD and any
  durable contracts/docs the slice must satisfy
- add `Blocked by` referencing other task IDs/filenames when slices depend on each other, and reserve
  files in dependency order so IDs sort naturally within each area
- add `### Specification` / `### Design` sections when the PRD slice needs task-local planned intent
  beyond acceptance criteria
- place the new task IDs on the roadmap only if the user wants the PRD scheduled (milestone heading for
  goal-level timing)

### 7. Report

List all created files with their phase counts, dependency order, and roadmap placement. Remind the
user that starting any existing task requires the pre-implementation review gate from
the `task-ledger` skill (references/todo-convention.md).

## Quality bar

- Each task is atomic, independently completable, and verifiable.
- Existing inbox ideas, tasks, docs, and code/tests were checked before task creation.
- New area rows were confirmed with the user before use.
- Optional `Repos` metadata uses slugs from `.config/repos.project.md`; repo slugs are not encoded into task IDs,
  filenames, prefixes, or areas.
- Optional `Autonomy` metadata is one of `L0`-`L3` and does not exceed the resolved repo max.
- Optional `Spec refs` preserves PRD, contract, or durable-doc relationships and does not imply that a
  planned spec is already implemented.
- Optional `Target date` / `Deadline` metadata is used only for explicit task-specific dates and uses
  `YYYY-MM-DD` or `N/A`.
- Ledgers and area pages are synced and pass `at ledger check`.
- Repo registry and task `Repos` / `Autonomy` metadata pass `at repos-check`.
