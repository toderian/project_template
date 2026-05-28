# <Area Name> - Dependency Graph

> Durable dependency map for `<area>`.
> Last reviewed: YYYY-MM-DD.

## Repo graph

Use repo slugs from `repos.project` when this project has a registry. Source path evidence should use
`<repo-slug>:<repo-relative-path>`, not absolute local checkout paths.

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
