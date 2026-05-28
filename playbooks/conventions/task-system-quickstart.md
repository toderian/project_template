# Task System Quickstart

## Purpose

This is the golden path for the project task system. Use it when you need the shortest reliable route
from a loose idea to completed, archived work.

For full details, use:

- `playbooks/conventions/inbox-convention.md` for raw ideas.
- `playbooks/conventions/todo-convention.md` for committed task files.
- `playbooks/skills/productivity/triage-inbox.md` for the discovery gate before task creation.

## Golden path

For multi-repo projects, set up `.config/repos.project.md` and `.local/repos.map` during
`_base/SETUP_INSTRUCTIONS.md` Phase 2c before creating tasks, so task-producing skills can fill
optional `Repos` metadata from stable repo slugs.

```text
/init
/capture-idea "rough idea or follow-up"
/triage-inbox          # discovery gate, then promote / drop / defer / append
/roadmap               # place task IDs in Urgent / Now / Next / Later / Someday
# Before implementing an existing task:
# run the pre-implementation review gate from todo-convention.md
# implement / execute the task
/complete-task <TASK-ID>
_base/scripts/sync-todo-ledgers.sh --check

# Periodic health check:
/audit-todos          # report-only audit of active tasks against code/tests/docs
```

Direct creation is also valid when the work is already clear:

```text
/init
/add-task "clear, actionable task"
/roadmap
# pre-implementation review gate
# implement / execute the task
/complete-task <TASK-ID>
_base/scripts/sync-todo-ledgers.sh --check
```

## Source of truth split

- **Inbox files** (`docs/tasks_manager/_inbox/I-NNN_*.md`) hold raw, low-commitment ideas. They are
  intentionally light and may be wrong, stale, or duplicated until triage proves otherwise.
- **Task files** (`docs/tasks_manager/_todos/<PREFIX>-NNN-<TYPE>_*.md`) own committed work details:
  status, priority, owner, phase checklists, acceptance criteria, related tests, execution log,
  completion harvest, and completion summary. When a downstream project has committed
  `.config/repos.project.md`, tasks may also include optional `Repos` metadata with comma-separated repo slugs.
- **Roadmap** (`docs/tasks_manager/_roadmap.md`) owns placement and order only: Urgent, Now, Next,
  Later, Someday. It references task IDs in any horizon; raw inbox IDs may sit only in `Someday` as
  parking-lot signals until `/triage-inbox` promotes or drops them. It does not duplicate task status
  or phase detail.
- **Generated ledgers and area pages** (`docs/tasks_manager/_active.md`, `docs/tasks_manager/_done.md`,
  `docs/areas/_overview.md`, generated blocks in `docs/areas/<slug>.md`) are derived views. Rebuild
  them with `_base/scripts/sync-todo-ledgers.sh`; validate them with `_base/scripts/sync-todo-ledgers.sh --check`.
- **Runbooks** (`docs/resources/<area>/runbooks/<scenario-slug>.md`) own sanitized, repeatable
  operational procedures. Local placeholder bindings live in ignored
  `.local/runbooks/<scenario-slug>.local.md`.
- **Raw knowledge files** (`docs/resources/_inbox/`) are staging for uploads awaiting
  `/distill-knowledge`; non-Markdown files there stay ignored by default.
- **Durable attachments** (`docs/resources/<area>/attachments/`) own long-lived committed `.docx`, PDF,
  spreadsheet, diagram, and similar source documents with nearby Markdown metadata.
- **Workbooks** (`workbooks/<workbook-slug>/`) own reusable working bundles with a workbook
  `README.md`, local scripts, data, assets, templates, examples, outputs, and declared dependencies.

## Active-task health checks

Use `/audit-todos` as the periodic active-task health check. It reads `docs/tasks_manager/_todos/`,
compares each task with current code, tests, docs, ledgers, roadmap placement, area pages, and
`docs/resources/`, then reports whether tasks should be kept, updated, closed, cancelled, split into
follow-ups, or escalated for a user decision.

The audit is report-only by default. It does not edit task files, archive tasks, create follow-ups, or
reorder the roadmap. Recommended mutations flow through `/complete-task`, `/capture-idea`, `/add-task`,
or `/roadmap` after the user chooses a next step.

## Discovery gate

`/triage-inbox` must run discovery before promoting an inbox idea. Capture is fast; triage is where the
agent checks reality.

For each idea, inspect likely matches in:

- other inbox ideas, including archived ones
- active and archived tasks
- `docs/tasks_manager/_roadmap.md`, ledgers, and area pages
- `docs/resources/` and `docs/archive/`
- `docs/resources/CONTEXT.md`, area summaries under `docs/resources/<area>/summary.md`, dependency
  graphs under `docs/resources/<area>/dependency-graph.md`, feature contracts under
  `docs/resources/<area>/contracts/*.md`, runbooks under `docs/resources/<area>/runbooks/*.md`,
  component contexts under `docs/resources/<area>/components/*/CONTEXT.md`, and `CONTEXT_DOCS_DIR`
  only if configured
- likely implementation files and tests

Classify the idea before asking for a decision:

- **duplicate inbox idea** - append useful details to the existing idea if chosen; archive the duplicate
  with a one-line reason.
- **already tracked task** - append useful details or a cross-link to the existing task if chosen;
  archive the inbox idea with a one-line reason.
- **already implemented** - archive the inbox idea with a one-line reason unless a distinct follow-up
  remains.
- **obsolete/stale** - archive the inbox idea with a one-line reason.
- **related but distinct** - promote only after recording the related IDs, docs, or code paths.
- **genuinely new** - promote normally if the user wants it committed.

Present the classification, evidence, and recommendation before creating or changing any task.

## Which command to use

- Use `/capture-idea` when the thought is vague, low-context, speculative, or simply worth remembering.
  It should stay fast: reserve an `I-NNN`, make a best-guess area, and avoid heavy research.
- Use `/add-task` when the work is clear enough to commit directly to the backlog with type, area,
  priority, phases, acceptance criteria, and tests.
- Use `/triage-inbox` when reviewing captured ideas. It performs discovery, then promotes, drops,
  defers, or appends details to existing work.
- Use `/prd-to-todos` when a PRD or larger design needs to be split into independently executable
  tasks.
- Use `/complete-task` when a task is done or intentionally cancelled. It verifies acceptance/tests,
  fills completion harvest and summary, archives the task, syncs generated views, and runs strict
  validation.
- Use `/audit-todos` when reviewing active tasks for drift. It classifies active tasks with evidence
  from code, tests, docs, roadmap, ledgers, and resources, then recommends follow-up workflows without
  mutating files by default.

## Minimum validation

After task-system changes, run:

```bash
_base/scripts/sync-todo-ledgers.sh
_base/scripts/sync-todo-ledgers.sh --check
_base/scripts/check-repos-config.sh
```

For template maintenance, also run:

```bash
./_base/scripts/check-template-update.sh
```
