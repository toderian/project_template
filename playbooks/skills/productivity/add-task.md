# Add Task

## Purpose

Create a full task directly in `docs/tasks_manager/_todos/` when the work is already clear enough to
commit to the backlog. This complements `capture-idea`: vague thoughts go to the inbox quickly, while
clear tasks get area, prefix, priority, phases, acceptance criteria, tests, and optional roadmap
placement immediately.

Follow `playbooks/conventions/todo-convention.md` for the file format and lifecycle.

Prerequisite: `docs/tasks_manager/` must already be initialized. If it is missing, run `/init` first.

## Process

### 1. Confirm this is a task, not an inbox idea

Use this skill when the user asks to add, create, file, or track a task and the request is already
actionable. If the request is vague, low-context, or mostly a thought for later, use `capture-idea`
instead.

Do not over-interview. Only ask when a required field cannot be inferred safely:

- area / prefix
- type (`F`, `D`, `C`, `R`)
- priority (`high`, `medium`, `low`)
- acceptance criteria

### 2. Check for duplicates and overlap

Scan:

- `docs/tasks_manager/_inbox/`
- `docs/tasks_manager/_inbox_archived/`
- `docs/tasks_manager/_todos/`
- `docs/tasks_manager/_todos_archived/`
- `docs/tasks_manager/_roadmap.md`
- `docs/areas/_overview.md` and relevant `docs/areas/<slug>.md` pages, if they exist
- `docs/resources/`, `docs/archive/`, root/component `CONTEXT.md`, and likely code/tests when the task
  appears tied to existing behavior

If the work appears already captured, tracked, or implemented, report the matching `I-NNN`, task ID,
doc, or code path and ask whether to append detail, link the existing item, or create a distinct task.
Do not merge, cancel, or archive tasks without explicit user approval.

### 3. Assign area and prefix

Read `docs/tasks_manager/_areas.md`.

- Pick the best existing area row.
- Use `global` / prefix `T` for default, global, or cross-area work.
- If no area fits, propose an `Area`, `Prefix`, `Description`, and `Page` row and ask before appending.

### 4. Shape the task

Create one atomic task. Fill:

- type (`F`, `D`, `C`, `R`)
- priority (`high`, `medium`, `low`)
- 2-4 sentence brief
- phases with checklists
- acceptance criteria
- related tests, or `N/A - <reason>`
- follow-ups (`None` if empty)
- execution log placeholder
- completion harvest placeholder with explicit `None` entries
- completion summary placeholder

Use `Source: add-task`. Set `Source ref` to an issue, PRD, inbox idea, conversation note, or `N/A`.
After choosing the type and short description, reserve the task file with
`scripts/reserve-work-item.sh task <PREFIX> <TYPE> <short-description>`. The helper creates the
placeholder atomically so parallel agents cannot claim the same ID.

### 5. Write the file

Fill the reserved path printed by:

```text
scripts/reserve-work-item.sh task <PREFIX> <TYPE> <short-description>
```

Use the template shape from `todo-convention.md`. Keep the short description lowercase, hyphenated, and
under 50 characters.

### 6. Sync and optionally schedule

Run:

```bash
scripts/sync-todo-ledgers.sh
scripts/sync-todo-ledgers.sh --check
```

If the user wants this scheduled, add the task ID to `docs/tasks_manager/_roadmap.md` under Now, Next,
or Later in the intended order, then run sync and `--check` again so `docs/areas/_overview.md` and
generated area blocks reflect the roadmap placement.

### 7. Report

Return:

- created task ID and file path
- area, type, priority
- whether it was placed on the roadmap
- any area row created

Remind the user only when relevant that starting implementation later requires the pre-implementation
review gate in `todo-convention.md`.

## Quality bar

- The filename passes `block-bad-todo-name.sh`.
- The task has the complete template required by `todo-convention.md`.
- The task ID uses the selected area's prefix and the next per-prefix counter.
- New area rows are user-approved and include a page path.
- Ledgers and area pages are synced and pass `scripts/sync-todo-ledgers.sh --check`.
- Roadmap placement is explicit; the skill does not silently schedule work.
