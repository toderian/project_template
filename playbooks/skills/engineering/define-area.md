# Define Area

## Purpose

Create or refresh durable knowledge for a domain or product capability that may span one repo or many
repos. Areas are long-lived capabilities such as `runtime-platform`, `billing-platform`, or
`search-indexing`. They are not one-off feature plans.

This workflow indexes real architecture so future agents can orient from `docs/resources/<area>/`
instead of rediscovering repo relationships, package names, install modes, and runtime dependencies.

Use `/cross-repo-feature` after an area exists to capture one concrete feature contract inside it.

## Agent Guidance

When guiding the user, enforce these defaults:

- Keep the area scoped to a durable capability. If the proposed area starts absorbing unrelated UI,
  API, runtime, infrastructure, and operations concerns, split it or record an open boundary question.
- Choose one canonical docs home before writing cross-repo docs. Prefer the central docs repo when it
  already exists and is clearly shared; otherwise use the initiating repo. Do not split one area's
  summary, dependency graph, and contracts across multiple repos.
- Use repo slugs from `repos.project` when that registry exists. If it is missing, propose creating it
  from `_base/repos.project.example` before committing cross-repo docs that need stable repo names.
- Record source paths as `<repo-slug>:<repo-relative-path>`, never as absolute local checkout paths
  from `.local/repos.map`.
- Treat source paths, package names, install modes, env/config keys, API schemas, Docker images, and
  generated artifacts as first-class area facts. They are common drift points, not incidental detail.
- Use `unknown` for unproven ownership or dependency edges. Do not fill gaps with plausible guesses.
- If the area supports independently deployed repos, record which repos can be upgraded separately and
  which version combinations must remain compatible.
- Add drift signals that tell future agents when to run `/refresh-context`, such as API schema files,
  env/config definitions, package manifests, Dockerfiles, generated SDK outputs, and contract docs.

## Source of Truth

The canonical in-repo area knowledge root is:

```text
docs/resources/<area>/
├── summary.md
├── dependency-graph.md
├── contracts/
└── components/
```

`docs/areas/<area>.md` remains the generated task-status page. It is useful work-status evidence, not
the durable architecture home.

When a central docs repo is configured through `CONTEXT_DOCS_DIR`, prefer
`$CONTEXT_DOCS_DIR/resources/<area>/` as the canonical home for cross-repo area docs after confirming
that the directory is meant to be shared project knowledge. Existing per-source external context under
`$CONTEXT_DOCS_DIR/<source-repo>/...` may still be read as fallback evidence.

## Process

### 1. Normalize the Area

Convert the requested name to a lowercase hyphenated slug. If the user gives an ambiguous label,
propose the slug and confirm it before writing files.

Check whether the area already exists in:

- `docs/resources/<area>/`
- `$CONTEXT_DOCS_DIR/resources/<area>/` when a central docs repo is configured
- `docs/tasks_manager/_areas.md` for task-prefix registration
- `docs/areas/<area>.md` for generated task status

Ask before creating a new area, changing the canonical docs home, or materially changing which repos
or components the area owns.

### 2. Discover Participant Repos

Start from the current repo, then look for sibling or nested independent Git checkouts when the user's
area name implies a multi-repo capability.

Gather evidence, not guesses:

- repo roots, remotes, current branches, `repos.project` rows when present, and whether each checkout
  is independent, a submodule, or a vendored copy
- `.gitmodules`, lockfiles, workspace files, Dockerfiles, compose files, CI files, and packaging files
- package names and import names from `package.json`, `pyproject.toml`, `setup.cfg`, `go.mod`,
  `Cargo.toml`, Gradle/Maven files, or equivalent local manifests
- runtime dependencies: images, services, env vars, ports, mounted paths, queues, event topics, CLI
  tools, generated artifacts, and schema locations
- install modes: packaged release, Docker/runtime install, local editable install, workspace link,
  source checkout, generated SDK, or manual copy
- known docs: READMEs, ADRs, runbooks, existing component contexts, generated API docs, issue/PR links,
  and task completion harvests

For colocated independent checkouts, record that relationship plainly. Do not call them submodules
unless `.gitmodules` or `git submodule status` proves it.

### 3. Write or Refresh the Area Summary

Create or update `summary.md` with concise, evidence-backed sections:

````md
# <Area Name> - Area Summary

> Durable cross-repo context for `<area>`.
> Last reviewed: YYYY-MM-DD.

## Responsibility
What this area owns and what it deliberately does not own.

## Participant repos
| Repo | Role | Package/import | Source paths | Install modes |
|------|------|----------------|--------------|---------------|

## Boundaries
APIs, schemas, events, messages, env vars, CLIs, Docker images, generated artifacts, and ownership
rules that other repos depend on.

## Runtime and development modes
How the repos are assembled in production/runtime images and how developers wire them locally.

## Known docs
Links to READMEs, ADRs, runbooks, component contexts, tasks, and external references.

## Open questions
Unresolved ownership, compatibility, rollout, or verification questions.
````

Do not duplicate detailed component context. Link to `docs/resources/<area>/components/...` instead.

### 4. Write or Refresh the Dependency Graph

Create or update `dependency-graph.md` with both human-readable edges and enough detail for future
agents to follow the area:

````md
# <Area Name> - Dependency Graph

> Durable dependency map for `<area>`.
> Last reviewed: YYYY-MM-DD.

## Repo graph
```text
repo-a -> repo-b -> package-name
repo-a -> package-name
```

## Relationships
| From | To | Kind | Runtime? | Development? | Evidence |
|------|----|------|----------|--------------|----------|

## Install modes
| Repo/package | Packaged/runtime | Local development | Notes |
|--------------|------------------|-------------------|-------|

## Drift signals
Files, manifests, or docs that should trigger `/refresh-context` when they change.
````

Prefer explicit "unknown" or "not found" entries over confident filler.

### 5. Align Task Areas When Needed

If the area should receive tracked tasks, register it in `docs/tasks_manager/_areas.md` only after
confirmation. Pick a unique uppercase prefix and let `_base/scripts/sync-todo-ledgers.sh` create or refresh
the generated `docs/areas/<area>.md` page.

Task-area registration is useful but not required for read-only architecture indexing. The durable
area docs remain under `docs/resources/<area>/`.

### 6. Report

End with:

- canonical area docs home
- repos inspected and repos included
- files written or refreshed
- uncertain ownership or dependency facts
- suggested next `/cross-repo-feature` contracts, if any
- commands/checks run

Use the shared status vocabulary:

```md
## Status: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
## Summary: ...
## Concerns: ...
## Files changed: ...
```

## Quality Bar

- The area boundary is confirmed when new or materially changed.
- The area is narrow enough to be useful; broad catch-all areas are split or flagged as open questions.
- The canonical docs home is explicit, especially when a central docs repo is available.
- Every participant repo and dependency edge is backed by a file, manifest, command output, registry
  row, or existing doc.
- Participant repo names are stable slugs from `repos.project` when the project has opted into the
  registry; source paths use `<repo-slug>:<repo-relative-path>`.
- The docs distinguish runtime dependencies from local development conveniences.
- Unknown ownership is reported as uncertainty, not rewritten into certainty.
- Version and deployment independence is recorded when participant repos can roll out separately.
- Future agents can find the feature contract home without asking where cross-repo work belongs.
