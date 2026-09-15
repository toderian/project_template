---
name: task-ledger
description: "Task/inbox file formats, ID reservation, area/repo registries, roadmap horizons, and the at ledger/reserve/repos-check tooling keeping docs/tasks_manager/ and docs/areas/ consistent. Use when creating, triaging, completing, or validating tasks/inbox ideas, or when another skill points here for the task file format."
metadata:
  source:
    [
      playbooks/conventions/task-system-quickstart.md,
      playbooks/conventions/todo-convention.md,
      playbooks/conventions/inbox-convention.md,
      _base/scripts/sync_todo_ledgers.py,
    ]
  pack: task-management
paths: ["docs/tasks_manager/**"]
---

# Task Ledger

## Purpose

This is the canonical home for the project task system: the inbox and task file formats, ID
reservation, the area and repo registries, roadmap horizons, and the ledger-sync tooling that derives
`docs/tasks_manager/_active.md`, `docs/tasks_manager/_done.md`, and the generated `docs/areas/` pages.
Other skills (`agents-tasks:add-task`, `agents-tasks:capture-idea`, `agents-tasks:triage-inbox`, `agents-tasks:complete-task`, `agents-tasks:roadmap`, `agents-tasks:prd-to-todos`,
`agents-tasks:tidy-repo`, `agents-tasks:audit-todos`, `agents-tasks:define-area`) point here rather than restating field rules or validation
behavior.

- [references/todo-convention.md](references/todo-convention.md) — task file format, filename grammar,
  ID counters, area registry, repo registry, spec lifecycle, roadmap semantics, ledger/area sync, and
  the completion/archive workflow.
- [references/inbox-convention.md](references/inbox-convention.md) — inbox file format, capture, and
  the six-way triage classification.
- [references/task-system-quickstart.md](references/task-system-quickstart.md) — the full quickstart:
  source-of-truth split, discovery gate, which command to use, and minimum validation.

## Golden path

Skill lines below use full ids: prefix an id with `/` in Claude Code or `$` in Codex.

```text
at init --with-tasks
agents-tasks:capture-idea "rough idea or follow-up"
agents-tasks:triage-inbox          # discovery gate, then promote / drop / defer / append
agents-tasks:roadmap                # place task IDs in Urgent / Now / Next / Later / Someday
# Before implementing an existing task:
# run the pre-implementation review gate from references/todo-convention.md
# implement / execute the task
agents-tasks:complete-task <TASK-ID>
at ledger check
```

Direct creation is also valid when the work is already clear:

```text
at init --with-tasks
agents-tasks:add-task "clear, actionable task"
agents-tasks:roadmap
# pre-implementation review gate
# implement / execute the task
agents-tasks:complete-task <TASK-ID>
at ledger check
```

`docs/tasks_manager/` must already be initialized with `at init --with-tasks` before any of
these steps. Task files remain the source of truth; the inbox, roadmap, and generated ledgers/area
pages are the other layers described in `references/task-system-quickstart.md` §"Source of truth
split".

## Tooling

- `at ledger sync` / `at ledger check` / `at ledger rotate-log <TASK-ID>` — wraps
  `scripts/sync_todo_ledgers.py`. `sync` regenerates `_active.md`, `_done.md`, `docs/areas/_overview.md`,
  and the generated blocks in each `docs/areas/<slug>.md`. `check` is read-only and fails (non-zero
  exit) on duplicate/ambiguous IDs, malformed required metadata, status-directory mismatches,
  unregistered areas/prefixes, bad roadmap references, and stale generated files; it only warns on an
  archived task's missing completion harvest, on tasks that are growing large (see "Task size" below),
  and on a `_runs/<TASK-ID>/` run directory whose task is archived or missing.
  `rotate-log` moves a task's `## Execution log` body into `docs/tasks_manager/_logs/<TASK-ID>.md`,
  leaving a short pointer in the task file.
- `at task brief <TASK-ID> --phase N` / `at task run-state init|check <TASK-ID>` — wraps
  `scripts/task_brief.py`. `brief` writes phase N of a task (plus the task brief, acceptance criteria,
  related tests, specification, design, and spec-ref paths — never the execution log or other phases)
  to `docs/tasks_manager/_runs/<TASK-ID>/phase-N/brief.md` as the sole context for an implementer
  subagent; `run-state init` writes the `_runs/<TASK-ID>/state.md` resume map with one row per phase
  and `run-state check` validates it (status vocabulary, row count, commit SHAs). Used by
  `agents-core:execute-plan`; the run directory is removed by `agents-tasks:complete-task`.
  `at task run <TASK-ID>` (shipped with agents-core) drives that skill's loop from a shell with one
  `claude -p` / `codex exec` process per dispatch.
- `at reserve inbox <slug>` / `at reserve task <PREFIX> <TYPE> <slug>` — wraps
  `scripts/reserve_work_item.sh`. Atomically creates the reserved placeholder file and prints its path
  so parallel agents cannot claim the same ID.
- `at repos-check [--local]` — wraps `scripts/check_repos_config.sh`. Validates
  `.config/repos.project.md` and task `Repos`/`Autonomy` metadata; `--local` also validates
  `.local/repos.map`.

## Task size

Large tasks and unbounded execution logs are hard to review and to keep in context. `at ledger check`
warns (does not fail) when a task file exceeds 400 lines, and separately when a task's `## Execution
log` section exceeds 200 lines — the second warning names the exact command to fix it:
`at ledger rotate-log <TASK-ID>`. Run that command to move the log body into
`docs/tasks_manager/_logs/<TASK-ID>.md` and keep only a pointer in the task file; new entries then go to
the rotated log file.

## After any edit

Run `at ledger check` after hand-editing any task file, inbox file, `_areas.md`, or `_roadmap.md`. It is
read-only, safe to run anytime, and is the fastest way to catch a malformed edit before it reaches a
commit or another agent picks up stale state. Follow it with `at repos-check` when the edit touched
`Repos` or `Autonomy` metadata.

## Quality bar

- Task and inbox files match the field tables, filename grammar, and status lifecycle in
  `references/todo-convention.md` / `references/inbox-convention.md`.
- `at ledger check` and `at repos-check` pass (warnings are acceptable; errors are not) before work is
  considered synced.
- Task IDs and inbox IDs are reserved with `at reserve`, never hand-picked, so concurrent agents cannot
  collide.
- Oversized tasks are rotated with `at ledger rotate-log` rather than left to grow unbounded.
