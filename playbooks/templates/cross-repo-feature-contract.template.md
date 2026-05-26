# <Feature Name> - Feature Contract

> Area: `<area>`
> Status: draft | accepted | implemented | superseded
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
