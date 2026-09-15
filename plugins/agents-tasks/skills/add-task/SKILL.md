---
name: add-task
description: "Create an area-prefixed task in docs/tasks_manager/_todos/ with a brief, phases, acceptance criteria, priority, optional spec/design sections, optional roadmap placement, and dates only when scheduling intent is explicit. Use when the user says \"add task\", \"create task\", \"file a task\", \"track this task\", or wants an existing task made implementation-ready with spec and design sections."
metadata:
  source: playbooks/skills/productivity/add-task.md
  pack: task-management
---

# Add Task

## Purpose

Create a task directly in `docs/tasks_manager/_todos/` when the work is already clear enough to
commit to the backlog, or make an existing task implementation-ready. Vague thoughts go to the inbox
through `agents-tasks:capture-idea`; clear tasks get an area, a type, a priority, a brief, phases and
acceptance criteria — and nothing else until it is needed.

The file format, lifecycle and validation live in the `agents-tasks:task-ledger` skill
(references/todo-convention.md). Prerequisite: `docs/tasks_manager/` exists (`at init --with-tasks`).

## Process

### 1. Confirm this is a task, not an inbox idea

Use this skill when the request is actionable. If it is vague, low-context, or a thought for later,
use `agents-tasks:capture-idea`. If the work is too big for one session and the way to the goal is
not yet visible, use `agents-tasks:wayfinder`.

Do not over-interview. Ask only when a required field cannot be inferred safely: area / prefix, type
(`F`, `D`, `C`, `R`), priority, acceptance criteria. Never ask for target dates or deadlines; add
them only when the user gives explicit scheduling intent.

### 2. Check for duplicates and overlap

Run the discovery scan from the `agents-tasks:task-ledger` skill §"Discovery gate" (inbox, active and
archived tasks, `_roadmap.md`, ledgers, area pages, `docs/resources/` + `docs/archive/`, and likely
code/tests when the task ties to existing behavior).

If the work appears already captured, tracked, or implemented, report the matching `I-NNN`, task ID,
doc, or code path and ask whether to append detail, link the existing item, or create a distinct task.
Do not merge, cancel, or archive tasks without explicit user approval.

### 3. Assign area and prefix

Read `docs/tasks_manager/_areas.md`. Pick the best existing area row; use `global` / prefix `T` for
default, global, or cross-area work. If no area fits, propose an `Area`, `Prefix`, `Description`, and
`Page` row and ask before appending.

If `.config/repos.project.md` exists, infer the relevant repo slugs and fill the optional `Repos` row
when the scope is clear; omit it otherwise. Fill the optional `Autonomy` row only when the task must
be stricter than the repo default (never above the repo `Autonomy max`).

### 4. Shape the task — the core, and only the core

Reserve the file first: `at reserve task <PREFIX> <TYPE> <short-description>` (lowercase, hyphenated,
under 50 characters). Then fill the reserved path with the core shape from `todo-convention.md`:

- metadata: Task ID, Type, Area, Created, Updated, Status `open`, Priority, `Source: add-task`
- title and a 2–4 sentence brief: the user outcome and the constraints that matter
- phases with checklists — **one phase is the default**; add a second only when it is separately
  committable and reviewable
- acceptance criteria: observable, testable, each one traceable to a phase item

Optional rows and sections (`Source ref`, `Related tests`, `Follow-ups`, `Spec refs`, dates, …) go in
only when they carry a real value now. Do not write an execution log, completion harvest, or
completion summary: the first execution appends the log and `agents-tasks:complete-task` writes the
rest.

Prefer fewer phases and fewer criteria. If the shape you are about to write has more than three
phases or a criterion that no phase delivers, stop and cut before saving (the
`agents-tasks:simplify-task` rules apply at creation too).

### 4b. Spec and design sections, when the criteria alone would lose intent

For a task whose behavior or approach needs agreement before code — a public interface, a data
change, several plausible designs, or open questions that change the architecture — add
`### Specification` and/or `### Design` and the `Spec refs` row per
[references/spec-sections.md](references/spec-sections.md). That reference also covers making an
**existing** task implementation-ready and the approval boundary before `agents-core:execute-plan`.

### 5. Sync and optionally schedule

```bash
at ledger sync
at ledger check
at repos-check        # only when the task carries Repos or Autonomy
```

If the user wants this scheduled, add the task ID to `docs/tasks_manager/_roadmap.md` under Urgent,
Now, Next, Later, or Someday in the intended order (horizon semantics: `todo-convention.md`
§Roadmap); goal-level timing goes under a `### Milestone: <name> (target|deadline: YYYY-MM-DD)`
heading inside the horizon. Run sync and check again afterwards.

### 6. Report

Return the task ID and path; area, type, priority; whether it was placed on the roadmap; any area row
created; and whether spec/design sections were added.

## Quality bar

- The filename passes `block-bad-todo-name.sh`; the ID uses the area's prefix and the next counter.
- The task has the core shape and no placeholder sections; optional rows carry real values or are
  absent.
- Acceptance criteria are testable and each maps to a phase item.
- Optional `Repos` / `Autonomy` / `Spec refs` / date rows follow the rules in `todo-convention.md`.
- New area rows are user-approved and include a page path.
- `at ledger check` (and `at repos-check` when relevant) pass; roadmap placement is explicit, never
  silent.
