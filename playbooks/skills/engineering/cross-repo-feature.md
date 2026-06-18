# Cross-Repo Feature

## Purpose

Capture a concrete feature contract inside a durable area. A feature contract is the shared agreement
for one change that crosses repo, package, runtime, or deployment boundaries.

Use this after `/define-area` has indexed the area. Examples:

- `service-request-signing`
- `dynamic-runtime-env`
- `extension-lifecycle`

## Source of Truth

Feature contracts live under the area's canonical knowledge root:

```text
docs/resources/<area>/contracts/<feature-slug>.md
```

When a central docs repo is configured through `CONTEXT_DOCS_DIR`, use
`$CONTEXT_DOCS_DIR/resources/<area>/contracts/<feature-slug>.md` after confirming that the central docs
repo is the canonical home for the area.

The contract links to `summary.md`, `dependency-graph.md`, `docs/resources/system-map.md`, and
relevant component contexts in the same area. It does not replace implementation tasks or PRDs; it
defines the shared cross-repo boundary that those tasks must satisfy.

## Agent Guidance

When guiding the user, enforce these defaults:

- Keep one contract to one concrete change. If the request mixes several independent outcomes, split it
  into multiple feature contracts under the same area.
- Make partial rollout explicit. Record expected behavior for old producer plus new consumer, new
  producer plus old consumer, and mixed deployment states whenever repos can deploy independently.
- Treat secrets, signing, auth headers, network IDs, API base URLs, env vars, config keys, Docker
  images, CLI flags, and generated artifacts as boundary contract fields, not implementation trivia.
- Every boundary needs a verification row. If no automated check exists, write `manual` or `missing`
  in the verification matrix and capture the gap as a follow-up instead of leaving it implicit.
- Prefer executable checks for high-risk boundaries. Docs-only contracts are acceptable for V1, but
  API/schema/env/Docker compatibility should grow tests or CI checks when the risk justifies it.
- Link implementation tasks and PRs back to the contract, and run `/refresh-context` during closeout
  when code changes affect recorded boundaries.
- Keep the contract `Status` honest: `accepted` is the target, `implemented` requires evidence, and
  mixed rollout states should use `partially-implemented` until all required boundaries are verified.
- Use repo slugs from `.config/repos.project.md` when that registry exists. If it is missing and the contract
  needs stable repo names, propose creating it from `_base/repos.project.example.md` first.
- Record source paths as `<repo-slug>:<repo-relative-path>`, never as absolute local checkout paths
  from `.local/repos.map`.

## Process

### 1. Require an Area Context

Before writing a feature contract, locate the area summary and dependency graph:

- `docs/resources/<area>/summary.md`
- `docs/resources/<area>/dependency-graph.md`
- or the matching central-docs paths under `$CONTEXT_DOCS_DIR/resources/<area>/`

If the area does not exist, run `/define-area` first or create only a minimal area stub after user
confirmation. Do not bury cross-repo contracts in a repo-local note.

### 2. Fix the Feature Slug

Normalize the feature name to a lowercase hyphenated slug. If a contract with that slug already
exists, refresh it in place rather than creating a near-duplicate.

### 3. Inspect the Boundary

Read the area docs, then inspect the smallest useful source set for the proposed change:

- participant repos and source paths recorded in `summary.md`
- dependency and install-mode rows in `dependency-graph.md`
- existing component contexts under `docs/resources/<area>/components/`
- API, schema, event, message, env, CLI, Docker, generated artifact, or packaging files touched by the
  feature
- task logs, PRDs, ADRs, issues, and completion harvests that mention the feature

If a participant repo or boundary is missing from the area docs, pause and refresh the area context
before writing the feature contract.

### 4. Write the Contract

Create or update:

```text
docs/resources/<area>/contracts/<feature-slug>.md
```

Use this structure:

```md
# <Feature Name> - Feature Contract

> Area: `<area>`
> Status: draft | accepted | partially-implemented | implemented | superseded
> Last reviewed: YYYY-MM-DD

## Intent
One to three sentences describing the user-visible or platform outcome.

## Participant responsibilities
| Repo/package | Responsibility | Source paths | Owner/unknown |
|--------------|----------------|--------------|---------------|

## Boundary contract
### APIs
Accepted request/response shapes, method names, versioning, and compatibility rules, or `None`.

### Schemas and data
Schemas, migrations, serialized data, generated artifacts, and compatibility rules, or `None`.

### Events and messages
Topics, payloads, ordering, idempotency, retry, and versioning rules, or `None`.

### Environment and configuration
Env vars, config keys, defaults, required/optional status, secrets handling, and rollout safety, or
`None`.

### CLI and Docker/runtime
Commands, flags, images, build args, entrypoints, volumes, install modes, and runtime assembly rules,
or `None`.

## Compatibility expectations
Supported old/new version combinations, deprecation rules, and what must fail closed.

## Rollout order
1. Repo/package step and why it must happen in that order.
2. Verification or migration gate.

## Verification matrix
| Boundary | Repo/package | Check | Required before |
|----------|--------------|-------|-----------------|
| API/schema/env/CLI/Docker/etc. | Repo or package name | Automated command, `manual`, or `missing` | Merge, deploy, release, or rollout step |

## Evidence
- `path-or-command` - what it proves

## Open questions
- Ownership, compatibility, rollout, or verification gaps that remain unresolved.
```

Keep every boundary section explicit. Write `None` when a boundary is irrelevant so future agents know
it was considered.

### 5. Cross-Link Tasks and Plans

If the feature will be implemented as work items, create or update tasks through the normal task
workflow and link the contract in each task's brief or related docs. The contract owns cross-repo
agreement; task files own execution status.

### 6. Report

End with:

- contract path
- repos and boundaries inspected
- compatibility and rollout expectations captured
- verification matrix gaps
- area docs that may need `/refresh-context`
- commands/checks run

Use the shared status vocabulary:

```md
## Status: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
## Summary: ...
## Concerns: ...
## Files changed: ...
```

## Quality Bar

- A durable area context exists before the contract is written.
- Repo responsibilities are explicit enough that each implementation task can be assigned.
- Repo names use stable `.config/repos.project.md` slugs when the project has opted into the registry; source
  paths use `<repo-slug>:<repo-relative-path>`.
- API/schema/event/message/env/CLI/Docker boundaries are either specified or explicitly marked `None`.
- Compatibility and rollout order are stated, not left as implementation folklore.
- Verification covers each participant repo and every boundary that can break independently; missing
  checks are named explicitly.
- Secrets, auth/signing, env/config, Docker/runtime, and generated artifacts are first-class contract
  sections when they exist.
