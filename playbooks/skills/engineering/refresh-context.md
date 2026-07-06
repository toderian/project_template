---
name: refresh-context
description: "Refresh the docs-primary knowledge base and detect stale architecture or domain context. Use when the user asks to \"refresh context\", \"reindex context\", \"update knowledge base\", or \"check context drift\"."
---

# Refresh Context

## Purpose

Refresh the repo's docs-primary knowledge base so future agents can orient from durable docs instead of
re-deriving architecture from scratch. Use this when the user asks to refresh, reindex, or drift-check
context after code, task, or documentation changes.

This skill updates existing knowledge-base docs only when there is evidence in code, task history, or
other docs. It is a maintenance workflow, not a brainstorming workflow.

## Source of Truth

The full path taxonomy — what lives under `docs/resources/` (glossary, `system-map.md`, area
`summary.md`/`dependency-graph.md`/`contracts/`/`runbooks/`/`attachments/`/`components/`, `_inbox`,
`_digests`) — is owned by `playbooks/conventions/knowledge-base-quickstart.md` §"Source of truth
split". Follow it rather than re-deriving paths here. Refresh-specific reminders:

- `docs/resources/CONTEXT.md` is the primary domain glossary; root `CONTEXT.md` is only a
  pointer/legacy fallback.
- Generated `docs/areas/<area>.md` pages belong to the ledger generator — never hand-edit them.
- Refresh uses curated `docs/resources/_digests/` as evidence; raw `_inbox/` processing belongs to
  `/distill-knowledge`.
- `.local/runbooks/` and `.local/repos.map` hold machine-local values and must not be cited in
  committed docs.

**`CONTEXT_DOCS_DIR` (stated once; applies everywhere below).** This is the external-storage escape
hatch for the writable knowledge root:

- **unset** → use the repo's in-repo `docs/resources/...` paths (the default for template repos);
- **set as the canonical central docs home for an area** → write area docs (summaries, dependency
  graphs, contracts, runbooks, component contexts) under `$CONTEXT_DOCS_DIR/resources/<area>/`;
- **set only for repo-specific external context** → write that repo's context docs under
  `$CONTEXT_DOCS_DIR/<source-repo>/`.

In both external modes, treat in-repo docs as fallback evidence. The path lists below are written for
the unset case; remap them per this rule when `CONTEXT_DOCS_DIR` is set.

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
registered area clearly owns the component (remapped per the `CONTEXT_DOCS_DIR` rule above when set).

## Process

### 1. Inventory the Current Knowledge Base

Determine the writable knowledge root per the `CONTEXT_DOCS_DIR` rule above, then list the docs that
can drift (in-repo paths shown; remap when `CONTEXT_DOCS_DIR` is set):

- domain glossary: `docs/resources/CONTEXT.md`
- area summaries: `docs/resources/<area>/summary.md`
- system map: `docs/resources/system-map.md`
- dependency graphs: `docs/resources/<area>/dependency-graph.md`
- feature contracts: `docs/resources/<area>/contracts/*.md`
- operational runbooks: `docs/resources/<area>/runbooks/*.md` and `docs/resources/global/runbooks/*.md`
- attachment metadata and indexes: `docs/resources/<area>/attachments/*.md`
- component contexts: `docs/resources/<area>/components/*/CONTEXT.md`
- source digests: `docs/resources/_digests/**/*.md`, plus supporting resources under `docs/resources/`
- task ledgers, active task files, done task files, execution logs, and completion harvests

Record each context doc's explicit review date and lifecycle status if it has one. For area docs,
capture participant repos and source paths from the system map, area summaries, dependency graphs, and
feature contracts. For component docs, also capture source paths from headers matching
`Architectural context for <repo>:<source-path>`. When `.config/repos.project.md` exists, verify
participant repo names against its slugs and keep source path references in
`<repo-slug>:<repo-relative-path>` form.

### 2. Discover the Changed Scope

Build a candidate change set from multiple signals:

- `git diff --name-only` for uncommitted changes.
- `git diff --name-only @{upstream}...HEAD` when an upstream branch exists.
- `git log --name-only --since=<last-reviewed-date>` for context docs that record a review date.
- `git log --name-only -20` when a relevant context doc has no review date.
- Active and done task logs, especially completion harvest sections.
- Participant repos and source paths recorded in area summaries, dependency graphs, and feature
  contracts.
- Participant repos, capability areas, critical flows, cross-repo boundaries, and drift signals
  recorded in `docs/resources/system-map.md`.
- Source paths recorded in component context headers.

Deduplicate the paths and separate code, docs, tasks, tests, generated ledgers, and deleted or moved
files. Treat generated docs as inputs to inspect only when their source ledger or task files explain
the change.

### 3. Map Files to Areas and Components

Map changed files to registered areas and known component docs before editing:

- Use the area registry and existing `docs/resources/<area>/summary.md` files to identify area
  ownership.
- Use `docs/resources/system-map.md` for top-level repo/capability orientation when present.
- Use existing `docs/resources/<area>/dependency-graph.md` and
  `docs/resources/<area>/contracts/*.md` to identify cross-repo participants and boundaries.
- Use existing `docs/resources/<area>/runbooks/*.md` only for stable operational procedures and safety
  notes; do not treat local bindings as committed evidence.
- Match component docs by their recorded source path first, then by slug only as a fallback.
- Prefer `global` for cross-area infrastructure, shared conventions, and default components.
- Ask the user before creating a new area or materially changing which area owns a component.

If ownership is ambiguous, skip the doc and report the uncertainty instead of inventing a boundary.

### 4. Research Before Editing

For each affected area or component, gather evidence from the smallest useful set of files:

- changed source and test files
- current area summary, dependency graph, feature contracts, or component context
- task logs and completion harvests that mention the behavior
- nearby docs under `docs/resources/`
- relevant source digests under `docs/resources/_digests/**/*.md`

When a subagent runtime is available and the scope splits cleanly, dispatch read-only researcher
subagents per area or component. Use the status vocabulary and report block from
`playbooks/skills/productivity/subagent-protocol.md`; the scope fence must forbid file edits and ask
for cited findings only. If no subagent runtime is available, inspect sequentially on the main thread.

### 5. Update Only Stale Docs

Edit a doc only when the evidence shows it is stale, incomplete, or pointing at the wrong source. Write
to the configured knowledge root:

- Update `docs/resources/CONTEXT.md` for domain vocabulary, relationships, and resolved ambiguities.
- Update `docs/resources/system-map.md` when participant repos, capability ownership, critical flows,
  cross-repo boundaries, status, evidence links, or drift signals changed.
- Update `docs/resources/<area>/summary.md` for durable area architecture, responsibilities,
  boundaries, and invariants.
- Update `docs/resources/<area>/dependency-graph.md` for participant repos, package/import names,
  runtime dependencies, install modes, and drift signals.
- Update `docs/resources/<area>/contracts/<feature-slug>.md` when an existing cross-repo feature
  contract's responsibilities, boundaries, compatibility expectations, rollout order, or verification
  matrix drifted.
- Update component `CONTEXT.md` files for public interface, ownership, dependencies, source path moves,
  tests, or important gotchas.
- Update runbooks only when a stable repeated procedure, placeholder, expected result, failure signal,
  or safety note has drifted. Keep private values in `.local/runbooks/`.
- When `CONTEXT_DOCS_DIR` is set, apply the corresponding updates under
  the configured central area root or repo-specific root rather than the source repo's in-repo docs.
- Leave generated `docs/areas/<area>.md` pages to the generator unless the user explicitly asks for a
  generator or ledger fix.

Do not promote guesses into docs. A `draft` or `accepted` spec is not current-state evidence. If the
code and task history imply an unresolved architecture question, add it to the final follow-up list
rather than writing a false certainty.

### 6. Report the Refresh

End with a concise report:

- docs updated, with the evidence source for each
- docs inspected but skipped because they were current
- docs skipped because ownership or facts were uncertain
- spec statuses changed or left unchanged, with evidence
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

- The refresh is docs-primary: durable docs under `docs/resources/` are the target, while
  `docs/areas/` remains generated task-status output.
- Every changed sentence is backed by code, task history, or existing docs.
- Planned specs (`draft`, `accepted`) are not reported as implemented behavior.
- Implemented claims have evidence from code, tests, task history, or reviewed docs.
- Root `CONTEXT.md` is not treated as the primary glossary when `docs/resources/CONTEXT.md` exists.
- Component paths remain traceable through exact `Architectural context for <repo>:<source-path>`
  headers.
- Cross-repo area docs remain traceable through participant repos, source paths, and evidence rows.
- Cross-repo source paths use stable repo slugs, not absolute local checkout paths.
- Ambiguous area ownership is escalated to the user instead of silently changed.
