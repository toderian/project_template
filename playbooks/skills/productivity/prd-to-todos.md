# PRD to Tasks

## Purpose

Extract actionable tasks from an existing PRD and create task files following the standard convention.

## Prerequisites

The project must have `docs/tasks_manager/_todos/` and `docs/tasks_manager/_areas.md` initialized. If
they do not exist, run `/init` first.

## Process

### 1. Locate the PRD

Ask the user for the PRD source. It can be:

- A GitHub issue number — fetch with `gh issue view <number>`
- A file path — read the file
- Already in the conversation context

### 2. Extract vertical slices

Break the PRD into actionable items. Prefer vertical slices (end-to-end through all layers) over horizontal slices (one layer at a time).

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

### 4. Quiz the user

Present the proposed tasks as a numbered list. For each:

- **Title**: short descriptive name
- **Area / prefix**: existing area row from `_areas.md`, or a proposed new area
- **Type**: `F` / `D` / `C` / `R`
- **Priority**: high / medium / low
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

### 5. Create task files

For each approved item, create a file in `docs/tasks_manager/_todos/` named
`<PREFIX>-NNN-<TYPE>_<short-desc>.md` following the full format in
`playbooks/conventions/todo-convention.md`, including:

- Metadata table with `Task ID` (next id for the area's prefix), `Type` (`F`/`D`/`C`/`R`),
  `Area` (a slug from `docs/tasks_manager/_areas.md`, defining a new row with the user if needed),
  `Source: prd-to-todos`, `Source ref` pointing to the PRD, `Priority`, and `Blocked by` (referencing
  other task IDs or filenames if dependent)
- Short human-readable title and 2-4 sentence brief
- Phases with per-phase checklists
- Acceptance criteria
- Related tests section (list known tests, or `N/A - <reason>`)
- Follow-ups section
- Empty execution log section (will be filled during execution)
- Empty completion harvest section
- Empty completion summary section

Assign consecutive IDs per prefix in dependency order so they sort naturally within each area. Use the
current datetime for the `Created` field. After creating the files, run `scripts/sync-todo-ledgers.sh`.
If the user wants the PRD scheduled, place the new task IDs on `docs/tasks_manager/_roadmap.md` in Now,
Next, or Later and run the sync again.

### 6. Report

List all created files with their phase counts, dependency order, and roadmap placement. Remind the
user that starting any existing task requires the pre-implementation review gate from
`playbooks/conventions/todo-convention.md`.
