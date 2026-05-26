# Triage Inbox

## Purpose

Turn captured ideas into committed work. Inbox capture is deliberately frictionless, so the inbox
accumulates raw `I-NNN` ideas; triage is the periodic, deliberate pass that decides whether each idea
should be promoted into a full area-prefixed task or dropped. This is where type, area prefix,
priority, phases, acceptance criteria, related tests, and optional roadmap placement get assigned.

Follow `playbooks/conventions/inbox-convention.md` (inbox side) and
`playbooks/conventions/todo-convention.md` (task side).

## Process

### 1. Gather

List the `new` ideas in `docs/tasks_manager/_inbox/` (Status `new`, not yet archived). Read each one. If the inbox is
empty, say so and stop.

### 2. Decide, per idea

Present the ideas to the user and decide each:

- **Promote** — worth doing. Continue to step 3.
- **Drop** — not worth doing (duplicate, obsolete, out of scope). Set the inbox file's `Status:
  dropped`, add a one-line reason in the body, and archive it (step 5).
- **Defer** — keep it as `new` for a later pass. Leave it untouched.

Let the user steer; don't unilaterally drop ideas. Batch the decisions in one exchange where possible.

### 3. Classify each promotion

For each promoted idea, settle:

- **Type** — `F` feature, `D` debug/bug, `C` chore/refactor, `R` research/spike.
- **Area and prefix** — pick a row from `docs/tasks_manager/_areas.md`. If none fits, this is the
  moment to define a new area with the user: propose an area slug, uppercase prefix, one-line
  description, and page path, confirm, append it to `_areas.md`, then use it.
- **Priority** — high / medium / low.
- **Roadmap placement** — leave unscheduled unless the user wants the new task in Now, Next, or Later.

### 4. Create the task

Assign the next `<PREFIX>-NNN` for the selected area (highest matching prefix across
`docs/tasks_manager/_todos/` + `docs/tasks_manager/_todos_archived/`, +1). Create
`docs/tasks_manager/_todos/<PREFIX>-NNN-<TYPE>_<short-desc>.md` per the task convention's full format:

- Metadata table including `Task ID`, `Type`, `Area`, `Source: inbox`, `Source ref: I-NNN`, and `Priority`.
- A short human-readable title and a 2-4 sentence brief.
- Phases with per-phase checklists.
- Acceptance criteria and a Related tests section, or `N/A - <reason>`.
- Follow-ups, execution log, completion harvest, and completion summary sections.

Then run `scripts/sync-todo-ledgers.sh` to update ledgers and area pages. If the user chose roadmap
placement, update `docs/tasks_manager/_roadmap.md` and run the sync again.

### 5. Close out the inbox file

Set the inbox file's `Status` to `promoted` (or `dropped`) and move it to `docs/tasks_manager/_inbox_archived/`, so
the inbox only ever shows live ideas. The promoted task's `Source ref: I-NNN` preserves the trail back.

### 6. Report

Summarize how many ideas were promoted (with their new task IDs, types, areas, and roadmap placement)
and how many were dropped. Run `scripts/sync-todo-ledgers.sh` at the end to ensure the ledgers and area
pages reflect every change.

## Quality bar

- Every promoted idea became a well-formed task (passes `block-bad-todo-name.sh`) with `Source ref`
  pointing back to its `I-NNN`.
- New areas were confirmed with the user before use and recorded in `docs/tasks_manager/_areas.md`.
- The inbox contains only `new` ideas afterward; promoted/dropped ones are in `_inbox_archived/`.
- `docs/tasks_manager/_active.md`, `docs/areas/_overview.md`, and generated per-area blocks are in sync.
