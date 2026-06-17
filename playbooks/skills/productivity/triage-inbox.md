# Triage Inbox

## Purpose

Turn captured ideas into committed work. Inbox capture is deliberately frictionless, so the inbox
accumulates raw `I-NNN` ideas; triage is the periodic, deliberate pass that decides whether each idea
should be promoted into a full area-prefixed task or dropped. This is where type, area prefix,
priority, phases, acceptance criteria, related tests, and optional scheduling get assigned when the
user intends to schedule the work.

Follow `playbooks/conventions/inbox-convention.md` (inbox side) and
`playbooks/conventions/todo-convention.md` (task side).

Prerequisite: `docs/tasks_manager/` must already be initialized. If it is missing, run `/init` first.

## Process

### 1. Gather

List the `new` ideas in `docs/tasks_manager/_inbox/` (Status `new`, not yet archived). Read each one. If the inbox is
empty, say so and stop.

### 2. Discovery gate, per idea

Before deciding whether to promote an idea, inspect the current project state. The goal is not
exhaustive proof; it is enough evidence to avoid creating tasks for duplicate, already tracked, already
implemented, obsolete, or stale work.

For each idea, inspect likely matches in:

- `docs/tasks_manager/_inbox/` and `docs/tasks_manager/_inbox_archived/`
- `docs/tasks_manager/_todos/` and `docs/tasks_manager/_todos_archived/`
- `docs/tasks_manager/_roadmap.md`, `docs/tasks_manager/_active.md`, and `docs/tasks_manager/_done.md`
- `docs/areas/_overview.md` and relevant `docs/areas/<slug>.md` pages
- `docs/resources/` and `docs/archive/`
- `docs/resources/CONTEXT.md`, area summaries under `docs/resources/<area>/summary.md`, dependency
  graphs under `docs/resources/<area>/dependency-graph.md`, feature contracts under
  `docs/resources/<area>/contracts/*.md`, runbooks under `docs/resources/<area>/runbooks/*.md`,
  component contexts under `docs/resources/<area>/components/*/CONTEXT.md`, and `CONTEXT_DOCS_DIR`
  only if configured
- likely code and tests found by searching for the idea's domain terms, filenames, commands, or symbols

Classify each idea as one of:

- **duplicate inbox idea** - the same raw idea already exists in the live or archived inbox.
- **already tracked task** - an active or archived task already covers the work.
- **already implemented** - code, docs, or tests show the requested outcome already exists.
- **obsolete/stale** - the idea no longer applies because the product, architecture, decision record, or
  task sequence moved on.
- **related but distinct** - it touches nearby work but still has a separate outcome.
- **genuinely new** - no meaningful duplicate, implementation, or existing task was found.

Present the classification, evidence, and recommendation to the user before promotion decisions. Cite
task IDs, inbox IDs, docs, code paths, or tests where they affected the recommendation.

### 3. Decide, per idea

Present the ideas to the user and decide each:

- **Promote** — worth doing and not already covered. Continue to step 4.
- **Drop** — duplicate, obsolete, already implemented, stale, or out of scope. Set the inbox file's
  `Status: dropped`, add a one-line reason in the body, and archive it (step 6).
- **Defer** — keep it as `new` for a later pass. Leave it untouched.
- **Append to existing** — when the idea is already tracked by another inbox idea or task, append useful
  detail or a cross-link to that existing file, then drop and archive the current inbox idea with a
  one-line reason such as `Merged into AUTH-001` or `Duplicate of I-007`.

Let the user steer; don't unilaterally drop ideas. Batch the decisions in one exchange where possible.

### 4. Shape each promotion

For each promoted idea, settle:

- **Type** — `F` feature, `D` debug/bug, `C` chore/refactor, `R` research/spike.
- **Area and prefix** — pick a row from `docs/tasks_manager/_areas.md`. If none fits, this is the
  moment to define a new area with the user: propose an area slug, uppercase prefix, one-line
  description, and page path, confirm, append it to `_areas.md`, then use it.
- **Repos** — if `.config/repos.project.md` exists and the relevant repo slugs are inferable, fill optional
  `Repos` metadata with comma-separated slugs. If not inferable, omit the row. Do not encode repo
  slugs into task IDs, filenames, prefixes, or areas.
- **Autonomy** — if the user explicitly asks for a loop autonomy level, or the task should be stricter
  than the repo default, fill optional `Autonomy` metadata with `L0`, `L1`, `L2`, or `L3`. Omit it
  otherwise. The value must not exceed the resolved repo `Autonomy max`.
- **Priority** — high / medium / low.
- **Dates** — add task `Target date` or `Deadline` only when the user or inbox item clearly gives a
  task-specific soft date or hard commitment. Omit both for normal promoted tasks.
- **Roadmap placement** — leave unscheduled unless the user wants the new task in Urgent, Now, Next,
  Later, or Someday. If the scheduling intent is goal-level timing, prefer a roadmap milestone heading
  over per-task dates.

### 5. Create the task

Reserve the task file with `_base/scripts/reserve-work-item.sh task <PREFIX> <TYPE> <short-desc>`, then fill
the printed path per the task convention's full format:

- Metadata table including `Task ID`, `Type`, `Area`, `Source: inbox`, `Source ref: I-NNN`, and `Priority`.
- Optional `Repos` metadata when inferable from `.config/repos.project.md`.
- Optional `Autonomy` metadata only when the task intentionally differs from the repo default/max.
- Optional `Target date` / `Deadline` metadata only when task-specific dates were explicitly provided.
- A short human-readable title and a 2-4 sentence brief.
- Optional `### Repo scope` section for cross-repo tasks when repo responsibilities need explanation.
- Phases with per-phase checklists.
- Acceptance criteria and a Related tests section, or `N/A - <reason>`.
- Follow-ups, execution log, completion harvest, and completion summary sections.

Then run `_base/scripts/sync-todo-ledgers.sh` to update ledgers and area pages. If the user chose
roadmap placement, update `docs/tasks_manager/_roadmap.md`; when they gave a target date, deadline, or
milestone, place the task under a dated milestone heading inside the chosen horizon. Run the sync again.
After all task, inbox, and roadmap changes are done, run `_base/scripts/sync-todo-ledgers.sh --check`
and `_base/scripts/check-repos-config.sh`.

### 6. Close out the inbox file

Set the inbox file's `Status` to `promoted` (or `dropped`) and move it to `docs/tasks_manager/_inbox_archived/`, so
the inbox only ever shows live ideas. The promoted task's `Source ref: I-NNN` preserves the trail back.

For dropped duplicates, obsolete ideas, and already implemented ideas, include the one-line reason in
the archived inbox file. For appended ideas, mention the file that received the useful details.

### 7. Report

Summarize how many ideas were promoted (with their new task IDs, types, areas, and roadmap placement)
and how many were dropped, deferred, or appended to existing work. Run `_base/scripts/sync-todo-ledgers.sh` at
the end to ensure the ledgers and area pages reflect every change, then run
`_base/scripts/sync-todo-ledgers.sh --check` and `_base/scripts/check-repos-config.sh`.

## Quality bar

- Every promoted idea became a well-formed task (passes `block-bad-todo-name.sh`) with `Source ref`
  pointing back to its `I-NNN`.
- Optional `Repos` metadata uses slugs from `.config/repos.project.md`; repo slugs are not encoded into task IDs,
  filenames, prefixes, or areas.
- Optional `Autonomy` metadata is one of `L0`-`L3` and does not exceed the resolved repo max.
- Optional `Target date` / `Deadline` metadata is used only for explicit task-specific dates and uses
  `YYYY-MM-DD` or `N/A`.
- New areas were confirmed with the user before use and recorded in `docs/tasks_manager/_areas.md`.
- The inbox contains only `new` ideas afterward; promoted/dropped ones are in `_inbox_archived/`.
- `docs/tasks_manager/_active.md`, `docs/areas/_overview.md`, and generated per-area blocks are in sync
  and pass `_base/scripts/sync-todo-ledgers.sh --check`.
- Repo registry and task `Repos` / `Autonomy` metadata pass `_base/scripts/check-repos-config.sh`.
- The discovery gate ran before task creation, and each promoted idea was checked for duplicates,
  existing tasks, already implemented behavior, stale context, related work, and relevant docs/code/tests.
