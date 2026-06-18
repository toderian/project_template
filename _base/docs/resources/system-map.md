# System Map

> Status: draft
> Last reviewed: N/A

This file is the top-level index for how the working repos fit together. Keep it concise and
evidence-backed. Link to area summaries, dependency graphs, feature contracts, component contexts,
runbooks, and task IDs instead of duplicating their details here.

## Status meanings

| Status | Meaning |
|--------|---------|
| `draft` | Proposed or rough; not approved and not implementation evidence. |
| `accepted` | Approved target behavior; not proof that the system already works this way. |
| `partially-implemented` | Some evidence exists; live and planned pieces must be separated. |
| `implemented` | Verified current behavior with evidence from code, tests, task history, or reviewed docs. |
| `superseded` | Obsolete; link the replacement or state why it no longer applies. |

## Participant repos

Use repo slugs from `.config/repos.project.md` when this project has a registry. Source paths should
use `<repo-slug>:<repo-relative-path>`, not absolute local checkout paths from `.local/repos.map`.

| Repo | Status | Role | Primary areas | Evidence |
|------|--------|------|---------------|----------|
| unknown | draft | Unknown until `/map-system` runs. | global | N/A |

## Capability areas

| Area | Status | Responsibility | Key docs | Evidence |
|------|--------|----------------|----------|----------|
| global | draft | Default, cross-area, and uncategorized work. | `docs/resources/global/summary.md` | N/A |

## Critical flows

| Flow | Status | Participating repos/areas | Contract or spec | Evidence |
|------|--------|---------------------------|------------------|----------|
| unknown | draft | unknown | N/A | N/A |

## Cross-repo boundaries

| Boundary | Status | Producer | Consumer | Contract | Evidence |
|----------|--------|----------|----------|----------|----------|
| unknown | draft | unknown | unknown | N/A | N/A |

## Drift signals

Files, manifests, schemas, generated artifacts, env/config definitions, Dockerfiles, CI workflows, or
task closeouts that should trigger `/refresh-context` or `/map-system`.

- N/A

## Refresh log

| Date | Action | Evidence | Follow-ups |
|------|--------|----------|------------|
| N/A | Initial seed. | N/A | Run `/map-system` when real repos are available. |

## Open questions

- Which repos and areas should be included in the canonical system picture?
