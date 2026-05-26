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
  It may include a generated pointer to the durable area context, but agents should not add durable
  architecture notes there.
- `docs/resources/<area>/summary.md` owns area-level architecture knowledge: responsibilities,
  important flows, decisions, open questions, and links to dependency graphs, contracts, and component
  contexts.
- `docs/resources/<area>/dependency-graph.md` owns cross-repo or cross-package dependency knowledge:
  repo/package relationships, runtime dependencies, install modes, and drift signals.
- `docs/resources/<area>/contracts/<feature-slug>.md` owns concrete cross-repo feature contracts:
  participant responsibilities, API/schema/event/env/CLI/Docker boundaries, compatibility, rollout,
  and verification.
- `docs/resources/<area>/components/<component-slug>/CONTEXT.md` owns component architecture:
  boundaries, public interfaces, dependencies, data ownership, tests, and invariants.
- `docs/resources/_inbox/` is the raw knowledge drop zone for documents, exports, notes, and pasted
  source material that has not been distilled yet. It is staging, not authoritative context.
- `docs/resources/_digests/<area>/` stores curated Markdown summaries of raw sources, segregated by
  owning area. Use `global/` for cross-cutting knowledge, `_cross-area/` for sources that materially
  affect several areas, and `_uncategorized/` when ownership is not known yet. A digest preserves
  source provenance and the important extracted facts before stable facts are promoted into canonical
  glossary, area, dependency, contract, or component docs.
- `CONTEXT_DOCS_DIR` is an external-storage escape hatch for describing a repo you should not write
  into. It is not the normal default for repos that use this template.

## Discovery Order

When `CONTEXT_DOCS_DIR` is unset, a skill that needs project language or architecture context should
look in this order:

1. `docs/resources/CONTEXT.md`
2. Root `CONTEXT.md` if it points to the docs-primary glossary or if no docs-primary glossary exists
3. `docs/resources/<area>/summary.md` for the relevant area
4. `docs/resources/<area>/dependency-graph.md` for repo/package relationships and install modes
5. `docs/resources/<area>/contracts/*.md` for feature-specific cross-repo agreements
6. `docs/resources/<area>/components/*/CONTEXT.md` for known component boundaries
7. `docs/resources/_digests/**/*.md` for source-backed summaries not yet promoted elsewhere
8. Legacy component context files stored beside source only as fallback evidence

Do not scan `docs/resources/_inbox/` as routine project context. Raw inbox files may be large,
duplicative, sensitive, or stale. Use `/distill-knowledge` when the task is to process that material.

When `CONTEXT_DOCS_DIR` is configured as a central docs repo, use
`$CONTEXT_DOCS_DIR/resources/<area>/` as the canonical writable home for shared cross-repo area docs,
including area summaries, dependency graphs, feature contracts, and component contexts. For
repo-specific external context, use `$CONTEXT_DOCS_DIR/<source-repo>/` as the writable knowledge root
for that source repo:

- `$CONTEXT_DOCS_DIR/<source-repo>/CONTEXT.md` for the domain glossary
- `$CONTEXT_DOCS_DIR/<source-repo>/resources/<area>/components/<component-slug>/CONTEXT.md` for
  component contexts

In-repo docs may still be read as fallback evidence, but routine updates go to the configured canonical
knowledge root.

Do not treat generated ledgers or generated area status blocks as architecture documentation. They are
evidence about work status, not durable knowledge.

## Raw knowledge ingestion

Use `docs/resources/_inbox/` as the drop zone for raw source material: PDFs, notes, exports, vendor
docs, design drafts, screenshots with text, transcripts, and research. Non-Markdown files in the seeded
folder are ignored by default so large or sensitive material is not committed accidentally; projects can
relax that rule in their downstream `.gitignore` if they intentionally version raw sources.

Run `/distill-knowledge` to process raw material. The workflow creates a digest at:

```text
docs/resources/_digests/<area-or-bucket>/YYYY-MM-DD-<source-slug>.md
```

Each digest should name the source, distillation date, digest bucket, affected areas, executive
summary, key facts, decisions and constraints, domain terms, architecture notes, risks, suggested
knowledge-base updates, and follow-ups. Promote only stable, source-backed facts from the digest into
canonical docs under `docs/resources/`; keep uncertain or one-off details in the digest.

If the raw source is sensitive, license-restricted, or too large to commit, keep it outside the repo or
leave it ignored in `_inbox/`. The committed digest should retain only the information the project is
allowed to keep.

## Area summaries

Create `docs/resources/<area>/summary.md` when an area has durable architecture knowledge worth
preserving. Keep it concise and evidence-backed. Link to task IDs, resources, ADRs, dependency graphs,
feature contracts, and component context docs instead of duplicating their contents.

Ask before creating a new area or materially changing which area owns a subsystem. Routine updates
inside an existing registered area do not need a separate area-ownership question.

Use `/define-area` when the area spans repos, packages, install modes, or runtime boundaries. Use
`/cross-repo-feature` for one concrete feature contract inside an existing area.

For cross-repo work, agents should guide users toward narrow area boundaries, one canonical docs home,
explicit version compatibility, first-class env/auth/Docker/runtime boundaries, and a verification
matrix that names missing checks instead of hiding them.

## Component contexts

The component doc path is:

```text
docs/resources/<area>/components/<component-slug>/CONTEXT.md
```

When `CONTEXT_DOCS_DIR` is configured as the central docs repo for the area, replace the repo-relative
prefix with the shared area root:

```text
$CONTEXT_DOCS_DIR/resources/<area>/components/<component-slug>/CONTEXT.md
```

When `CONTEXT_DOCS_DIR` is configured only for repo-specific external context, keep the source repo
namespace:

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
