# AGENTS.md

> **Auto-loaded entrypoint for the agent operating contract.** Both Claude Code and Codex load this file automatically at session start.
>
> **First instruction to every agent:** before acting, also read [`_base/AGENTS.md`](./_base/AGENTS.md) in this directory. `_base/AGENTS.md` is the authoritative base contract; this `AGENTS.md` is the downstream-owned entrypoint that may add project-specific overrides below. Treat the two files as a single contract, with overrides in this file taking precedence over the base.

## How this file is structured

This is the **base template's** `AGENTS.md`. It is intentionally minimal because the template itself has no project-specific overrides to make.

When this template is seeded into a new project:

- `_base/AGENTS.md` is **upstream-owned**: do not edit it downstream. It updates cleanly via `git fetch template && git merge`.
- `AGENTS.md` (this file) is **downstream-owned**: each project replaces the "Project-specific overrides" section below with its own rules. Future template improvements to `AGENTS.md` will be rare; when they happen, downstream projects merge by hand.

## Project-specific overrides

_None for the base template itself._

Downstream projects, replace this section with rules that are specific to your project — for example:

- domain language and key invariants unique to this codebase
- repo-specific commands (test, lint, deploy) and their gotchas
- areas of the code that have non-obvious constraints
- people, teams, or stakeholders to coordinate with for certain changes

Anything not listed here falls through to `_base/AGENTS.md`.

## Per-directory overrides (monorepos)

For monorepos, place an `AGENTS.md` in any subdirectory to override or extend the root contract for that area. Subdirectory files should reference the root contract (this file + `_base/AGENTS.md`) and specify only what differs. Supported by Claude Code; Codex reads only the root `AGENTS.md`.
