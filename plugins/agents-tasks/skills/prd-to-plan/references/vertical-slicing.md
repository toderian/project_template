# Vertical Slicing Convention

## Purpose

Shared rules for breaking a PRD (or any large piece of work) into tracer-bullet vertical slices.
Used by `prd-to-plan`, `prd-to-issues`, and (for its tracer-bullet framing) `prd-to-todos` — each of
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

## Quiz-the-user pattern

Present the proposed breakdown as a numbered list, then ask the user whether the granularity feels
right (too coarse / too fine) and whether any items should be merged or split further. Iterate until
approved. Each destination skill adds its own fields to the list item (for example: user stories
covered, HITL/AFK type and blockers for issues, or the full task-metadata field set for tasks) — that
part is destination-specific and stays in the individual skill, not here.
