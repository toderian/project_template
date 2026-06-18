# Map System

## Purpose

Create or refresh `docs/resources/system-map.md`, the status-aware index of the project's working
repos, capability areas, critical flows, cross-repo boundaries, drift signals, and open questions.

Use this when the user asks to map the system, index working repos, understand how repos fit together,
or refresh architecture after teammates changed code or docs.

## Source of Truth

The system map is an index. It links to detailed sources instead of duplicating them:

- `.config/repos.project.md` for stable repo slugs and repo policy
- `.local/repos.map` for local checkout paths, never committed or cited directly
- `docs/resources/<area>/summary.md` for area responsibilities
- `docs/resources/<area>/dependency-graph.md` for repo/package/runtime relationships
- `docs/resources/<area>/contracts/*.md` for concrete feature contracts
- `docs/resources/<area>/components/*/CONTEXT.md` for component boundaries
- task completion harvests and execution logs for implementation evidence

Use lifecycle statuses consistently: `draft`, `accepted`, `partially-implemented`, `implemented`, and
`superseded`.

## Process

### 1. Choose Scope

Decide whether the run is:

- top-level orientation for all configured repos
- a focused capability/area refresh
- a drift check after recent teammate changes

If `.config/repos.project.md` exists, validate it with `_base/scripts/check-repos-config.sh`. If local
checkout inspection is needed, validate `.local/repos.map` with `_base/scripts/check-repos-config.sh
--local`. If no repo registry exists, inspect only the current repo unless the user explicitly names
other checkouts.

### 2. Gather Evidence

Inspect the smallest useful source set:

- repo registry rows and current repo remotes
- area summaries, dependency graphs, contracts, component contexts, runbooks, and sources ledgers
- package manifests, workspace files, Dockerfiles, compose files, CI workflows, schemas, generated
  artifacts, env/config definitions, and README files
- recent task completion harvests and execution logs

Use `<repo-slug>:<repo-relative-path>` in committed docs. Never write absolute paths from
`.local/repos.map`.

### 3. Update the System Map

Create or refresh `docs/resources/system-map.md` with these sections:

- participant repos
- capability areas
- critical flows
- cross-repo boundaries
- drift signals
- refresh log
- open questions

Each row that describes a repo, area, flow, or boundary must carry a lifecycle status and evidence. Use
`unknown` or `N/A` instead of guessing.

If detailed area docs are missing or stale, do not expand the system map into a full architecture
document. Record an open question or recommend `define-area` / `refresh-context`.

### 4. Reconcile Task and Spec Links

When the map identifies planned but unimplemented work, link to existing tasks or recommend task
creation. When it identifies implemented behavior, cite evidence from code, tests, task history, or
reviewed docs.

Do not mark an area, flow, or boundary `implemented` without evidence.

### 5. Report

End with:

- system map path
- repos and docs inspected
- status changes made
- missing area docs or contracts
- drift signals added
- open questions and suggested next tasks
- commands/checks run

Use the shared status vocabulary:

```md
## Status: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
## Summary: ...
## Concerns: ...
## Files changed: ...
```

## Quality Bar

- `system-map.md` remains an index, not a duplicate architecture manual.
- Every implemented claim has evidence.
- Planned specs are labeled `draft` or `accepted`.
- Mixed states use `partially-implemented` and separate live from planned behavior.
- Repo references use stable slugs, not local absolute paths.
- Missing or uncertain ownership is reported instead of invented.
