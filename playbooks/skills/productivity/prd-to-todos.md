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

### 4. Check for existing work

Before asking the user to approve task creation, compare the proposed slices against:

- `docs/tasks_manager/_inbox/` and `docs/tasks_manager/_inbox_archived/`
- `docs/tasks_manager/_todos/` and `docs/tasks_manager/_todos_archived/`
- `docs/tasks_manager/_roadmap.md`, ledgers, and area pages
- `docs/resources/`, `docs/archive/`, `docs/resources/CONTEXT.md`, area summaries, component contexts,
  and likely code/tests

If a slice is already captured, tracked, implemented, obsolete, or related-but-distinct, show the
evidence with the proposed task list. Ask whether to skip it, append detail to the existing item, link
it from the new task, or keep it as a distinct task. Do not create duplicate committed work silently.

### 5. Quiz the user

Present the proposed tasks as a numbered list. For each:

- **Title**: short descriptive name
- **Area / prefix**: existing area row from `_areas.md`, or a proposed new area
- **Repos**: if `repos.project` exists, comma-separated repo slugs when inferable, or omitted when not
  clear
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

### 6. Create task files

For each approved item, reserve a file in `docs/tasks_manager/_todos/` named
`<PREFIX>-NNN-<TYPE>_<short-desc>.md` and fill it following the full format in
`playbooks/conventions/todo-convention.md`, including:

- Metadata table with `Task ID` (next id for the area's prefix), `Type` (`F`/`D`/`C`/`R`),
  `Area` (a slug from `docs/tasks_manager/_areas.md`, defining a new row with the user if needed),
  optional `Repos` when inferable from `repos.project`,
  `Source: prd-to-todos`, `Source ref` pointing to the PRD, `Priority`, and `Blocked by` (referencing
  other task IDs or filenames if dependent)
- Short human-readable title and 2-4 sentence brief
- Optional `### Repo scope` section for cross-repo tasks when repo responsibilities need explanation
- Phases with per-phase checklists
- Acceptance criteria
- Related tests section (list known tests, or `N/A - <reason>`)
- Follow-ups section
- Empty execution log section (will be filled during execution)
- Completion harvest placeholder with explicit `None` rows
- Completion summary placeholder

Reserve each file with `_base/scripts/reserve-work-item.sh task <PREFIX> <TYPE> <short-desc>` in dependency
order so IDs sort naturally within each area. Fill each reserved placeholder immediately. Use the
current datetime for the `Created` field. After creating the files, run `_base/scripts/sync-todo-ledgers.sh`.
If the user wants the PRD scheduled, place the new task IDs on `docs/tasks_manager/_roadmap.md` in Now,
Next, or Later and run the sync again. After all task and roadmap changes are done, run
`_base/scripts/sync-todo-ledgers.sh --check` and `_base/scripts/check-repos-config.sh`.

### 7. Report

List all created files with their phase counts, dependency order, and roadmap placement. Remind the
user that starting any existing task requires the pre-implementation review gate from
`playbooks/conventions/todo-convention.md`.

## Quality bar

- Each task is atomic, independently completable, and verifiable.
- Existing inbox ideas, tasks, docs, and code/tests were checked before task creation.
- New area rows were confirmed with the user before use.
- Optional `Repos` metadata uses slugs from `repos.project`; repo slugs are not encoded into task IDs,
  filenames, prefixes, or areas.
- Ledgers and area pages are synced and pass `_base/scripts/sync-todo-ledgers.sh --check`.
- Repo registry and task `Repos` metadata pass `_base/scripts/check-repos-config.sh`.
