# Add Task

## Purpose

Create a full task directly in `docs/tasks_manager/_todos/` when the work is already clear enough to
commit to the backlog. This complements `capture-idea`: vague thoughts go to the inbox quickly, while
clear tasks get area, prefix, priority, phases, acceptance criteria, tests, and optional roadmap
placement immediately.

Follow `playbooks/conventions/todo-convention.md` for the file format and lifecycle.

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

- `docs/tasks_manager/_todos/`
- `docs/tasks_manager/_todos_archived/`
- `docs/tasks_manager/_roadmap.md`
- `docs/areas/_overview.md` and relevant `docs/areas/<slug>.md` pages, if they exist

If the work appears already tracked, report the matching task ID and ask whether to append detail to the
existing task or create a distinct task. Do not merge or cancel tasks without explicit user approval.

### 3. Assign area, prefix, and ID

Read `docs/tasks_manager/_areas.md`.

- Pick the best existing area row.
- Use `global` / prefix `T` for default, global, or cross-area work.
- If no area fits, propose an `Area`, `Prefix`, `Description`, and `Page` row and ask before appending.
- Assign the next `<PREFIX>-NNN` by scanning both `_todos/` and `_todos_archived/` for that prefix.

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

### 5. Write the file

Create:

```text
docs/tasks_manager/_todos/<PREFIX>-NNN-<TYPE>_<short-description>.md
```

Use the template shape from `todo-convention.md`. Keep the short description lowercase, hyphenated, and
under 50 characters.

### 6. Sync and optionally schedule

Run:

```bash
scripts/sync-todo-ledgers.sh
```

If the user wants this scheduled, add the task ID to `docs/tasks_manager/_roadmap.md` under Now, Next,
or Later in the intended order, then run the sync again so `docs/areas/_overview.md` and generated
area blocks reflect the roadmap placement.

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
- Ledgers and area pages are synced.
- Roadmap placement is explicit; the skill does not silently schedule work.
