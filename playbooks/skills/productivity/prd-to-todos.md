# PRD to Todos

## Purpose

Extract actionable todos from an existing PRD and create todo files following the standard convention.

## Prerequisites

The project must have `docs/_todos/` initialized. If it doesn't exist, run `/init` first or create it.

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

Present the proposed todos as a numbered list. For each:

- **Title**: short descriptive name
- **Priority**: high / medium / low
- **Phases**: list of committable steps
- **Acceptance criteria**: overall criteria for the todo to be done
- **Related tests**: known test files that will be affected or created
- **Blocked by**: which other todos must complete first (if any)

Ask the user:

- Is the granularity right?
- Do the phases make sense as commit points?
- Should any items be merged or split?
- Are any items missing?

Iterate until approved.

### 5. Create todo files

For each approved item, create a file in `docs/_todos/` named `T-NNN-<TYPE>_<short-desc>.md` following
the full format in `playbooks/conventions/todo-convention.md`, including:

- Metadata table with `Task ID` (next id per the convention's ID counters), `Type` (`F`/`D`/`C`/`R`),
  `Area` (a slug from `docs/_areas.md`, defining a new one with the user if needed), `Source:
  prd-to-todos`, `Source ref` pointing to the PRD, `Priority`, and `Blocked by` (referencing other
  todo filenames if dependent)
- Phases with per-phase checklists
- Acceptance criteria
- Related tests section (list known tests, mark unknown ones as TBD)
- Empty execution log section (will be filled during execution)
- Empty completion summary section

Assign consecutive Task IDs in dependency order so they sort naturally. Use the current datetime for the
`Created` field. After creating the files, add their rows to `docs/_active.md` (or run
`scripts/sync-todo-ledgers.sh`).

### 6. Report

List all created files with their phase counts and dependency order. Remind the user that during execution, each phase should be committed separately and the execution log should be updated in the todo file.
