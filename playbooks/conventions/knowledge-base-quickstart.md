# Knowledge Base Quickstart

## Purpose

This convention defines where durable project knowledge lives in template-inherited repos. The goal is
that agents can refresh context without guessing whether a root file, task page, or co-located note is
authoritative.

## Source of truth split

- `docs/resources/CONTEXT.md` owns the project domain language: canonical terms, relationships,
  resolved ambiguities, and example dialogue.
- The top-level `CONTEXT.md` is a pointer to `docs/resources/CONTEXT.md`. Treat an existing
  substantive root glossary as a legacy fallback and prefer moving future edits to `docs/resources/`.
- `docs/areas/<area>.md` remains the generated task-status page from `scripts/sync-todo-ledgers.sh`.
  Human notes outside generated markers are allowed, but it is not the durable architecture summary.
- `docs/areas/<area>/summary.md` owns area-level architecture knowledge: responsibilities, important
  flows, decisions, open questions, and links to component contexts.
- `docs/resources/<area>/components/<component-slug>/CONTEXT.md` owns component architecture:
  boundaries, public interfaces, dependencies, data ownership, tests, and invariants.
- `CONTEXT_DOCS_DIR` is an external-storage escape hatch for describing a repo you should not write
  into. It is not the normal default for repos that use this template.

## Discovery Order

When `CONTEXT_DOCS_DIR` is unset, a skill that needs project language or architecture context should
look in this order:

1. `docs/resources/CONTEXT.md`
2. Root `CONTEXT.md` if it points to the docs-primary glossary or if no docs-primary glossary exists
3. `docs/areas/<area>/summary.md` for the relevant area
4. `docs/resources/<area>/components/*/CONTEXT.md` for known component boundaries
5. Legacy component context files stored beside source only as fallback evidence

When `CONTEXT_DOCS_DIR` is configured, use `$CONTEXT_DOCS_DIR/<source-repo>/` as the writable
knowledge root for that source repo:

- `$CONTEXT_DOCS_DIR/<source-repo>/CONTEXT.md` for the domain glossary
- `$CONTEXT_DOCS_DIR/<source-repo>/areas/<area>/summary.md` for area summaries
- `$CONTEXT_DOCS_DIR/<source-repo>/resources/<area>/components/<component-slug>/CONTEXT.md` for
  component contexts

In-repo docs may still be read as fallback evidence, but routine updates go to the configured external
knowledge root.

Do not treat generated ledgers or generated area status blocks as architecture documentation. They are
evidence about work status, not durable knowledge.

## Area summaries

Create `docs/areas/<area>/summary.md` when an area has durable architecture knowledge worth preserving.
Keep it concise and evidence-backed. Link to task IDs, resources, ADRs, and component context docs
instead of duplicating their contents.

Ask before creating a new area or materially changing which area owns a subsystem. Routine updates
inside an existing registered area do not need a separate area-ownership question.

## Component contexts

The component doc path is:

```text
docs/resources/<area>/components/<component-slug>/CONTEXT.md
```

When `CONTEXT_DOCS_DIR` is configured, replace the repo-relative prefix with the external knowledge
root:

```text
$CONTEXT_DOCS_DIR/<source-repo>/resources/<area>/components/<component-slug>/CONTEXT.md
```

Derive `<component-slug>` from the source path:

1. Lowercase the source path.
2. Replace path separators and every non-alphanumeric run with `-`.
3. Collapse duplicate dashes.
4. Trim leading and trailing dashes.

Examples:

- `src/Auth/sessionStore.ts` -> `src-auth-sessionstore-ts`
- `packages/billing-api/` -> `packages-billing-api`
- `web/components/Order.Card.tsx` -> `web-components-order-card-tsx`

The first blockquote in every component context must record the exact source path:

```md
> Architectural context for <repo>:<source-path>
```

Use the registered area that clearly owns the component. Cross-area, global, or default components go
under `docs/resources/global/components/...`.

## Refreshing

Use `/refresh-context` when code, task logs, or recent colleague work may have made the knowledge base
stale. A refresh updates only docs supported by evidence from code, tasks, existing docs, or recorded
review notes. If ownership or architecture is uncertain, record the uncertainty and optionally capture
a follow-up inbox idea rather than inventing structure.
