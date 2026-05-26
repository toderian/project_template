# Refresh Context

## Purpose

Refresh the repo's docs-primary knowledge base so future agents can orient from durable docs instead of
re-deriving architecture from scratch. Use this when the user asks to refresh, reindex, or drift-check
context after code, task, or documentation changes.

This skill updates existing knowledge-base docs only when there is evidence in code, task history, or
other docs. It is a maintenance workflow, not a brainstorming workflow.

## Source of Truth

Keep these locations distinct:

- `docs/resources/CONTEXT.md` is the primary domain glossary.
- Root `CONTEXT.md` is only a pointer or fallback for older repos.
- Area architecture summaries live at `docs/areas/<area>/summary.md`.
- Generated area status pages remain at `docs/areas/<area>.md`; do not hand-edit generated status
  pages when the ledger generator owns them.
- Component contexts live at
  `docs/resources/<area>/components/<component-slug>/CONTEXT.md`.
- `CONTEXT_DOCS_DIR` is only an external-storage escape hatch for repos whose context docs cannot live
  in the source repo. When set, use `$CONTEXT_DOCS_DIR/<source-repo>/` as the writable knowledge root
  for glossary, area summary, and component context updates. Do not use it as the default layout for
  this template's docs-primary workflow.

## Component Slugs

Derive `<component-slug>` from the source path:

1. Lowercase the path.
2. Replace path separators and non-alphanumeric characters with `-`.
3. Collapse duplicate dashes.
4. Trim leading and trailing dashes.

The component doc header must preserve the exact source path, not the slug:

```md
> Architectural context for <repo>:<source-path>
```

For cross-area or default components, write under `docs/resources/global/components/...` unless a
registered area clearly owns the component. If `CONTEXT_DOCS_DIR` is configured, write the same
area/component shape under `$CONTEXT_DOCS_DIR/<source-repo>/resources/...`.

## Process

### 1. Inventory the Current Knowledge Base

First determine the writable knowledge root:

- If `CONTEXT_DOCS_DIR` is unset, use the repo's docs-primary paths.
- If `CONTEXT_DOCS_DIR` is set, use `$CONTEXT_DOCS_DIR/<source-repo>/` for context docs and treat
  in-repo docs as fallback evidence.

List the docs that can drift:

- domain glossary: `docs/resources/CONTEXT.md`, or `$CONTEXT_DOCS_DIR/<source-repo>/CONTEXT.md` when
  external storage is configured
- area summaries: `docs/areas/<area>/summary.md`, or
  `$CONTEXT_DOCS_DIR/<source-repo>/areas/<area>/summary.md` when external storage is configured
- component contexts: `docs/resources/<area>/components/*/CONTEXT.md`, or
  `$CONTEXT_DOCS_DIR/<source-repo>/resources/<area>/components/*/CONTEXT.md` when external storage is
  configured
- supporting resources under `docs/resources/`
- task ledgers, active task files, done task files, execution logs, and completion harvests

Record each context doc's explicit review date if it has one. For component docs, also capture source
paths from headers matching `Architectural context for <repo>:<source-path>`.

### 2. Discover the Changed Scope

Build a candidate change set from multiple signals:

- `git diff --name-only` for uncommitted changes.
- `git diff --name-only @{upstream}...HEAD` when an upstream branch exists.
- `git log --name-only --since=<last-reviewed-date>` for context docs that record a review date.
- `git log --name-only -20` when a relevant context doc has no review date.
- Active and done task logs, especially completion harvest sections.
- Source paths recorded in component context headers.

Deduplicate the paths and separate code, docs, tasks, tests, generated ledgers, and deleted or moved
files. Treat generated docs as inputs to inspect only when their source ledger or task files explain
the change.

### 3. Map Files to Areas and Components

Map changed files to registered areas and known component docs before editing:

- Use the area registry and existing `docs/areas/<area>/summary.md` files to identify area ownership.
- Match component docs by their recorded source path first, then by slug only as a fallback.
- Prefer `global` for cross-area infrastructure, shared conventions, and default components.
- Ask the user before creating a new area or materially changing which area owns a component.

If ownership is ambiguous, skip the doc and report the uncertainty instead of inventing a boundary.

### 4. Research Before Editing

For each affected area or component, gather evidence from the smallest useful set of files:

- changed source and test files
- current area summary or component context
- task logs and completion harvests that mention the behavior
- nearby docs under `docs/resources/`

When a subagent runtime is available and the scope splits cleanly, dispatch read-only researcher
subagents per area or component. Use the status vocabulary and report block from
`playbooks/skills/productivity/subagent-protocol.md`; the scope fence must forbid file edits and ask
for cited findings only. If no subagent runtime is available, inspect sequentially on the main thread.

### 5. Update Only Stale Docs

Edit a doc only when the evidence shows it is stale, incomplete, or pointing at the wrong source. Write
to the configured knowledge root:

- Update `docs/resources/CONTEXT.md` for domain vocabulary, relationships, and resolved ambiguities.
- Update `docs/areas/<area>/summary.md` for durable area architecture, boundaries, dependencies, and
  invariants.
- Update component `CONTEXT.md` files for public interface, ownership, dependencies, source path moves,
  tests, or important gotchas.
- When `CONTEXT_DOCS_DIR` is set, apply the corresponding updates under
  `$CONTEXT_DOCS_DIR/<source-repo>/...` rather than the source repo's in-repo docs.
- Leave generated `docs/areas/<area>.md` pages to the generator unless the user explicitly asks for a
  generator or ledger fix.

Do not promote guesses into docs. If the code and task history imply an unresolved architecture
question, add it to the final follow-up list rather than writing a false certainty.

### 6. Report the Refresh

End with a concise report:

- docs updated, with the evidence source for each
- docs inspected but skipped because they were current
- docs skipped because ownership or facts were uncertain
- follow-up inbox ideas for unresolved architecture questions
- commands or checks run

Use the shared status vocabulary:

```md
## Status: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
## Summary: ...
## Concerns: ...
## Files changed: ...
```

## Quality Bar

- The refresh is docs-primary: durable docs under `docs/resources/` and `docs/areas/` are the target,
  not ad hoc notes.
- Every changed sentence is backed by code, task history, or existing docs.
- Root `CONTEXT.md` is not treated as the primary glossary when `docs/resources/CONTEXT.md` exists.
- Component paths remain traceable through exact `Architectural context for <repo>:<source-path>`
  headers.
- Ambiguous area ownership is escalated to the user instead of silently changed.
