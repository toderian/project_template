# Task System Quickstart

## Purpose

This is the golden path for the project task system. Use it when you need the shortest reliable route
from a loose idea to completed, archived work.

For full details, use:

- [inbox-convention.md](inbox-convention.md) for raw ideas.
- [todo-convention.md](todo-convention.md) for committed task files.
- the `agents-tasks:triage-inbox` skill for the discovery gate before task creation.

## Golden path

For multi-repo projects, set up `.config/repos.project.md` and `.local/repos.map` with
`at init --with-repos` before creating tasks, so task-producing skills can fill optional `Repos`
metadata from stable repo slugs and honor optional `Autonomy max` ceilings.

Skill lines below use full ids: prefix an id with `/` in Claude Code or `$` in Codex.

```text
at init --with-tasks
agents-tasks:capture-idea "rough idea or follow-up"
agents-tasks:triage-inbox          # discovery gate, then promote / drop / defer / append
agents-tasks:roadmap               # place task IDs in Urgent / Now / Next / Later / Someday
# Before implementing an existing task:
# write the current-state note (todo-convention.md §"Before implementing an existing task")
# implement / execute the task
agents-tasks:complete-task <TASK-ID>
at ledger check

# Periodic health check:
agents-tasks:audit-todos          # report-only audit of active tasks against code/tests/docs
```

Direct creation is also valid when the work is already clear:

```text
at init --with-tasks
agents-tasks:add-task "clear, actionable task"
agents-tasks:roadmap
# current-state note (todo-convention.md §"Before implementing an existing task")
# implement / execute the task
agents-tasks:complete-task <TASK-ID>
at ledger check
```

## Source of truth split

- **Inbox files** (`docs/tasks_manager/_inbox/I-NNN_*.md`) hold raw, low-commitment ideas. They are
  intentionally light and may be wrong, stale, or duplicated until triage proves otherwise.
- **Task files** (`docs/tasks_manager/_todos/<PREFIX>-NNN-<TYPE>_*.md`) own committed work details:
  status, priority, owner, phase checklists, acceptance criteria, related tests, execution log,
  completion harvest, and completion summary. When a downstream project has committed
  `.config/repos.project.md`, tasks may also include optional `Repos` metadata with comma-separated repo slugs.
  Tasks may include optional `Autonomy` metadata (`L0`-`L3`) when they intentionally lower the repo
  ceiling or request a repo-allowed higher loop level. Tasks may include optional `Target date` and
  `Deadline` metadata (`YYYY-MM-DD` or `N/A`) only when the user explicitly provides task-specific
  scheduling intent. Tasks may include optional `Spec refs` metadata plus `### Specification` and
  `### Design` sections when executable work needs a task-local spec. Those sections are planned
  intent until the task is completed and linked durable specs are reconciled.
- **Roadmap** (`docs/tasks_manager/_roadmap.md`) owns placement and order only. It references task IDs
  in any horizon and may group them with dated milestone headings inside those horizons; raw inbox IDs
  may sit only in `Someday` as parking-lot signals until `agents-tasks:triage-inbox` promotes or drops them. It does
  not duplicate task status or phase detail. Horizon semantics and soft thresholds live in
  [todo-convention.md](todo-convention.md) §Roadmap.
- **Generated ledgers and area pages** (`docs/tasks_manager/_active.md`, `docs/tasks_manager/_done.md`,
  `docs/areas/_overview.md`, generated blocks in `docs/areas/<slug>.md`) are derived views. Rebuild
  them with `at ledger sync`; validate them with `at ledger check`.
- **Runbooks** (`docs/resources/<area>/runbooks/<scenario-slug>.md`) own sanitized, repeatable
  operational procedures. Local placeholder bindings live in ignored
  `.local/runbooks/<scenario-slug>.local.md`.
- **Raw knowledge files** (`docs/resources/_inbox/`) are staging for uploads awaiting
  `agents-tasks:distill-knowledge`; related files from one source event may be grouped in an inbox batch folder,
  and non-Markdown files there stay ignored by default.
- **System map** (`docs/resources/system-map.md`) is the status-aware index of participant repos,
  capability areas, critical flows, and cross-repo boundaries. It links to area summaries, dependency
  graphs, contracts, and component contexts instead of duplicating them.
- **Area source history** (`docs/resources/<area>/sources.md`) records teammate inputs, call batches,
  uploaded documents, durable attachments, why each source was added, and links to digests, tasks, or
  canonical docs.
- **Durable attachments** (`docs/resources/<area>/attachments/`) own long-lived committed `.docx`, PDF,
  spreadsheet, diagram, and similar source documents with nearby Markdown metadata.
- **Workbooks** (`workbooks/<workbook-slug>/`) own reusable working bundles with a workbook
  `README.md`, local scripts, data, assets, templates, examples, outputs, and declared dependencies.

## Active-task health checks

Use `agents-tasks:audit-todos` as the periodic active-task health check. It reads `docs/tasks_manager/_todos/`,
compares each task with current code, tests, docs, ledgers, roadmap placement, area pages, and
`docs/resources/`, then reports whether tasks should be kept, updated, closed, cancelled, split into
follow-ups, or escalated for a user decision.

The audit is report-only by default. It does not edit task files, archive tasks, create follow-ups, or
reorder the roadmap. Recommended mutations flow through `agents-tasks:complete-task`, `agents-tasks:capture-idea`, `agents-tasks:add-task`,
or `agents-tasks:roadmap` after the user chooses a next step.

## Discovery gate

`agents-tasks:triage-inbox` must run discovery before promoting an inbox idea. Capture is fast; triage is where the
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

Classify the idea before asking for a decision, using the six-way scheme defined in
[inbox-convention.md](inbox-convention.md) (duplicate inbox idea, already tracked task, already
implemented, obsolete/stale, related but distinct, genuinely new). That convention is the canonical
owner of what each classification means and the archive/promote action it implies.

Present the classification, evidence, and recommendation before creating or changing any task.

## Which command to use

- Use `agents-tasks:capture-idea` when the thought is vague, low-context, speculative, or simply worth remembering.
  It should stay fast: reserve an `I-NNN`, make a best-guess area, and avoid heavy research.
- Use `agents-tasks:add-task` when the work is clear enough to commit directly to the backlog with type, area,
  priority, phases, acceptance criteria, and tests.
- Use `agents-core:task-spec-workflow` when an existing task or clear idea needs a task-local Specification,
  Design, acceptance criteria, tests, and spec references before implementation.
- Use `agents-tasks:triage-inbox` when reviewing captured ideas. It performs discovery, then promotes, drops,
  defers, or appends details to existing work.
- Use `agents-tasks:prd-to-todos` when a PRD or larger design needs to be split into independently executable
  tasks.
- Use `agents-tasks:complete-task` when a task is done or intentionally cancelled. It verifies acceptance/tests,
  reconciles linked specs, fills completion harvest and summary, archives the task, syncs generated
  views, and runs strict validation.
- Use `agents-tasks:map-system` when the project needs a refreshed repo/capability system picture. It updates
  `docs/resources/system-map.md` and points detailed area work to `agents-tasks:define-area`.
- Use `agents-tasks:audit-todos` when reviewing active tasks for drift. It classifies active tasks with evidence
  from code, tests, docs, roadmap, ledgers, and resources, then recommends follow-up workflows without
  mutating files by default.

## Minimum validation

After task-system changes, run:

```bash
at ledger sync
at ledger check
at repos-check
```
