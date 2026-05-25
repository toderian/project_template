# Triage Inbox

## Purpose

Turn captured ideas into committed work. Inbox capture is deliberately frictionless, so the inbox
accumulates raw `I-NNN` ideas; triage is the periodic, deliberate pass that decides — for each idea —
whether to **promote** it into a full `T-NNN` todo or **drop** it. This is where types, areas, phases,
and acceptance criteria get assigned, because now there's a decision to make rather than a thought to
catch.

Follow `playbooks/conventions/inbox-convention.md` (inbox side) and
`playbooks/conventions/todo-convention.md` (todo side).

## Process

### 1. Gather

List the `new` ideas in `docs/_inbox/` (Status `new`, not yet archived). Read each one. If the inbox is
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
- **Area** — pick a slug from `docs/_areas.md`. If none fits, this is the moment to **define a new
  area with the user**: propose a slug + one-line description, confirm, append it to `docs/_areas.md`,
  then use it. (This is the "areas defined with the agent" workflow.)
- **Priority** — high / medium / low.

### 4. Create the todo

Assign the next `T-NNN` (highest across `docs/_todos/` + `docs/_todos_archived/`, +1). Create
`docs/_todos/T-NNN-<TYPE>_<short-desc>.md` per the todo convention's full format:

- Metadata table including `Task ID`, `Type`, `Area`, `Source: inbox`, `Source ref: I-NNN`, `Priority`.
- Phases with per-phase checklists (think: where are the natural commit points?).
- Acceptance criteria and a Related tests section.
- Empty execution log and completion summary sections.

Then add the new todo's row to `docs/_active.md` (or run `scripts/sync-todo-ledgers.sh`).

### 5. Close out the inbox file

Set the inbox file's `Status` to `promoted` (or `dropped`) and move it to `docs/_inbox_archived/`, so
the inbox only ever shows live ideas. The promoted todo's `Source ref: I-NNN` preserves the trail back.

### 6. Report

Summarize: how many promoted (with their new `T-NNN` ids, types, areas) and how many dropped. Run
`scripts/sync-todo-ledgers.sh` at the end to ensure the ledgers reflect every change.

## Quality bar

- Every promoted idea became a well-formed todo (passes `block-bad-todo-name.sh`) with `Source ref`
  pointing back to its `I-NNN`.
- New areas were confirmed with the user before use and recorded in `docs/_areas.md`.
- The inbox contains only `new` ideas afterward; promoted/dropped ones are in `_inbox_archived/`.
- `docs/_active.md` lists the new todos; ledgers are in sync.
