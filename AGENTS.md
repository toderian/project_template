# AGENTS.md

> **Auto-loaded entrypoint for the agent operating contract.** Both Claude Code and Codex load this file automatically at session start.
>
> **First instruction to every agent:** before acting, also read [`_base/AGENTS.md`](./_base/AGENTS.md) in this directory. `_base/AGENTS.md` is the authoritative base contract; this `AGENTS.md` is the downstream-owned entrypoint that may add project-specific overrides below. Treat the two files as a single contract, with overrides in this file taking precedence over the base.

## How this file is structured

This is the **base template's** `AGENTS.md`. It is intentionally small and contains only the
downstream-owned conventions that should seed new projects.

When this template is seeded into a new project:

- `_base/AGENTS.md` is **upstream-owned**: do not edit it downstream. It updates cleanly via `git fetch template && git merge`.
- `AGENTS.md` (this file) is **downstream-owned**: each project replaces or extends the
  "Project-specific overrides" section below with its own rules. Future template improvements to
  `AGENTS.md` will be rare; when they happen, downstream projects merge by hand.

## Project-specific overrides

### Local credentials

- Real credentials may live in `.creds/` at the repository root. This folder is local-only and must
  remain uncommitted; the root `.gitignore` ignores `.creds/`.
- Agents may read files in `.creds/` only when credentialed access is required for the task. Prefer
  explicit filenames from the user; if discovery is needed, list filenames without printing file
  contents.
- Never echo, paste, summarize, commit, or copy credential values from `.creds/` into tracked files,
  docs, logs, prompts, final answers, or task artifacts. If a needed credential is missing, state the
  expected `.creds/<filename>` path without inventing a value.

Downstream projects, replace or extend this section with rules that are specific to your project — for example:

- domain language and key invariants unique to this codebase
- repo-specific commands (test, lint, deploy) and their gotchas
- areas of the code that have non-obvious constraints
- people, teams, or stakeholders to coordinate with for certain changes

Anything not listed here falls through to `_base/AGENTS.md`.

## Per-directory overrides (monorepos)

For monorepos, place an `AGENTS.md` in any subdirectory to override or extend the root contract for that area. Subdirectory files should reference the root contract (this file + `_base/AGENTS.md`) and specify only what differs. Supported by Claude Code; Codex reads only the root `AGENTS.md`.
