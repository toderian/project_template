---
name: triage-inbox
description: "Review captured inbox ideas (docs/tasks_manager/_inbox/) and promote worthwhile ones into full area-prefixed tasks, or drop them. Use when the user says \"triage inbox\", \"review the inbox\", \"process my ideas\", \"clear the inbox\", or wants to turn captured ideas into actionable tasks."
---

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

Before deciding whether to promote an idea, run the discovery scan from
`playbooks/conventions/task-system-quickstart.md` §"Discovery gate" (inbox + archived inbox, active +
archived tasks, roadmap/ledgers/`_active.md`/`_done.md`/area pages, `docs/resources/` + `docs/archive/`
and their area docs, `CONTEXT_DOCS_DIR` if configured, and likely code/tests). The goal is not
exhaustive proof; it is enough evidence to avoid creating tasks for duplicate, already tracked, already
implemented, obsolete, or stale work.

Classify each idea using the six-way scheme defined in
`playbooks/conventions/inbox-convention.md` (duplicate inbox idea, already tracked task, already
implemented, obsolete/stale, related but distinct, genuinely new). That convention is the canonical
owner of each classification's meaning and the archive/promote action it implies.

Present the classification, evidence, and recommendation to the user before promotion decisions. Cite
task IDs, inbox IDs, docs, code paths, or tests where they affected the recommendation.

### 3. Decide, per idea

Present the ideas to the user and decide each:

- **Promote** — worth doing and not already covered. Continue to step 4.
- **Drop** — duplicate, obsolete, already implemented, stale, or out of scope. Set the inbox file's
  `Status: dropped`, add a one-line reason in the body, and archive it (step 5).
- **Defer** — keep it as `new` for a later pass. Leave it untouched.
- **Append to existing** — when the idea is already tracked by another inbox idea or task, append useful
  detail or a cross-link to that existing file, then drop and archive the current inbox idea with a
  one-line reason such as `Merged into AUTH-001` or `Duplicate of I-007`.

Let the user steer; don't unilaterally drop ideas. Batch the decisions in one exchange where possible.

### 4. Shape and create each promoted task

For each promoted idea, create the task exactly as `add-task` does — its steps 3–6 are the canonical
ritual for area/prefix, type, priority, the optional `Repos`/`Autonomy`/`Spec refs`/date metadata, the
full `todo-convention.md` file shape, `reserve-work-item.sh` reservation, and the
`sync-todo-ledgers.sh` + `--check` + `check-repos-config.sh` sync. Do not restate those field rules
here. Triage-specific overrides:

- set `Source: inbox` and `Source ref: I-NNN` on the promoted task so the trail back is preserved
- if no area fits, this is the moment to define a new area with the user (propose slug, uppercase
  prefix, one-line description, and page path; confirm; append to `_areas.md`; then use it)
- leave the task unscheduled unless the user wants roadmap placement; for goal-level timing prefer a
  roadmap milestone heading over per-task dates

### 5. Close out the inbox file

Set the inbox file's `Status` to `promoted` (or `dropped`) and move it to `docs/tasks_manager/_inbox_archived/`, so
the inbox only ever shows live ideas. The promoted task's `Source ref: I-NNN` preserves the trail back.

For dropped duplicates, obsolete ideas, and already implemented ideas, include the one-line reason in
the archived inbox file. For appended ideas, mention the file that received the useful details.

### 6. Report

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
