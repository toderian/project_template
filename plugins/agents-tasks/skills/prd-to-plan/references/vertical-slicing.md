# Vertical Slicing Convention

## Purpose

Shared rules for breaking a PRD (or any large piece of work) into tracer-bullet vertical slices.
Used by `agents-tasks:prd-to-plan`, `agents-extras:prd-to-issues`, and (for its tracer-bullet framing) `agents-tasks:prd-to-todos` — each of
those skills owns its own destination-specific output shape and "quiz the user" field list; this doc
owns only the slicing rules and the shared quiz pattern that all three build on.

A vertical slice cuts through **all** integration layers end-to-end (schema, API, UI, tests) for one
thin piece of user-visible behavior. A horizontal slice does one layer at a time across many features.
Tracer bullets are vertical slices: each one proves the path works end-to-end before the next is built.

## Slice rules

- Each slice delivers a narrow but COMPLETE path through every layer (schema, API, UI, tests)
- A completed slice is demoable or verifiable on its own
- Prefer many thin slices over few thick ones
- Do NOT include specific file names, function names, or implementation details that are likely to
  change as later phases are built
- DO include durable decisions: route paths, schema shapes, data model names
- Each slice is sized to fit in a single fresh context window
- Any prefactoring goes first: make the change easy, then make the easy change

## Exception: wide refactors

A **wide refactor** is one mechanical change — rename a column, retype a shared symbol, swap a
logging call — whose **blast radius** fans across the whole codebase, so a single edit breaks
thousands of call sites at once and no vertical slice can land green. Don't force it into a tracer
bullet. Sequence it as **expand → migrate → contract**:

1. **Expand.** Add the new form beside the old one so nothing breaks. One slice.
2. **Migrate.** Move call sites over in batches sized by blast radius — per package, per directory —
   each batch its own slice, blocked by the expand. CI stays green batch to batch because the old
   form still exists.
3. **Contract.** Delete the old form once no caller remains, blocked by every migrate batch.

When even the batches cannot stay green on their own, keep the sequence but let them share an
integration branch that all of them block, and promise green only at a final integrate-and-verify
slice.

## Quiz-the-user pattern

Present the proposed breakdown as a numbered list, then ask the user whether the granularity feels
right (too coarse / too fine) and whether any items should be merged or split further. Iterate until
approved. Each destination skill adds its own fields to the list item (for example: user stories
covered, HITL/AFK type and blockers for issues, or the full task-metadata field set for tasks) — that
part is destination-specific and stays in the individual skill, not here.
