# Task System Quickstart

## Purpose

This is the golden path for the project task system. Use it when you need the shortest reliable route
from a loose idea to completed, archived work.

For full details, use:

- `playbooks/conventions/inbox-convention.md` for raw ideas.
- `playbooks/conventions/todo-convention.md` for committed task files.
- `playbooks/skills/productivity/triage-inbox.md` for the discovery gate before task creation.

## Golden path

```text
/init
/capture-idea "rough idea or follow-up"
/triage-inbox          # discovery gate, then promote / drop / defer / append
/roadmap               # place task IDs in Now / Next / Later
# Before implementing an existing task:
# run the pre-implementation review gate from todo-convention.md
# implement / execute the task
/complete-task <TASK-ID>
scripts/sync-todo-ledgers.sh --check
```

Direct creation is also valid when the work is already clear:

```text
/init
/add-task "clear, actionable task"
/roadmap
# pre-implementation review gate
# implement / execute the task
/complete-task <TASK-ID>
scripts/sync-todo-ledgers.sh --check
```

## Source of truth split

- **Inbox files** (`docs/tasks_manager/_inbox/I-NNN_*.md`) hold raw, low-commitment ideas. They are
  intentionally light and may be wrong, stale, or duplicated until triage proves otherwise.
- **Task files** (`docs/tasks_manager/_todos/<PREFIX>-NNN-<TYPE>_*.md`) own committed work details:
  status, priority, owner, phase checklists, acceptance criteria, related tests, execution log,
  completion harvest, and completion summary.
- **Roadmap** (`docs/tasks_manager/_roadmap.md`) owns placement and order only: Now, Next, Later. It
  references task IDs in `Now` / `Next`; raw inbox IDs may sit in `Later` as parking-lot signals until
  `/triage-inbox` promotes or drops them. It does not duplicate task status or phase detail.
- **Generated ledgers and area pages** (`docs/tasks_manager/_active.md`, `docs/tasks_manager/_done.md`,
  `docs/areas/_overview.md`, generated blocks in `docs/areas/<slug>.md`) are derived views. Rebuild
  them with `scripts/sync-todo-ledgers.sh`; validate them with `scripts/sync-todo-ledgers.sh --check`.

## Discovery gate

`/triage-inbox` must run discovery before promoting an inbox idea. Capture is fast; triage is where the
agent checks reality.

For each idea, inspect likely matches in:

- other inbox ideas, including archived ones
- active and archived tasks
- `docs/tasks_manager/_roadmap.md`, ledgers, and area pages
- `docs/resources/` and `docs/archive/`
- `docs/resources/CONTEXT.md`, area summaries under `docs/areas/<area>/summary.md`, component contexts
  under `docs/resources/<area>/components/*/CONTEXT.md`, and `CONTEXT_DOCS_DIR` only if configured
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

## Minimum validation

After task-system changes, run:

```bash
scripts/sync-todo-ledgers.sh
scripts/sync-todo-ledgers.sh --check
```

For template maintenance, also run:

```bash
./_base/scripts/check-skills-sync.sh
git diff --check
```
