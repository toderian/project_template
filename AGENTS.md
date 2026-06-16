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

### Saved prompts

- Reusable or historically useful prompts that should travel with the repository belong under
  `.prompts/`. This directory is intentionally committable; do not add prompts there unless their
  contents are meant to become part of project history.
- Before committing anything from `.prompts/`, review it for credentials, private data, copied
  sensitive context, or other material that should not be preserved in Git. Being in `.prompts/` does
  not make a prompt safe to commit.
- Prompts that should remain local-only belong under `.no-commit/.prompts/`.

### Python tooling environments

- Use `uv` for persistent repo-level Python tooling dependencies. Do not use `pip install` directly
  for dependencies that should be represented in committed project state.
- Keep the default Python tooling environment under `tools/python/`, not at the repo root:
  `tools/python/pyproject.toml` declares tooling dependencies, `tools/python/uv.lock` records the
  exact resolved dependency state, and `tools/python/.python-version` pins the interpreter. Commit
  those files once Python tooling dependencies exist.
- Keep `tools/python/.venv/` local-only and uncommitted; the root `.gitignore` ignores it. A root
  `.venv/` is also ignored for local scratch environments.
- Run `uv` commands from `tools/python/`, for example `cd tools/python && uv sync`. Use `uv add`,
  `uv remove`, `uv lock`, `uv sync`, and `uv run` for managed tooling dependencies and commands.
- If a project needs multiple Python tooling environments, create explicit subfolders such as
  `tools/python/<name>/` and document each environment in the downstream `AGENTS.md`.
- Do not create `tools/python/pyproject.toml`, `tools/python/uv.lock`, or
  `tools/python/.python-version` until there are real Python tooling dependencies to represent.

Downstream projects, replace or extend this section with rules that are specific to your project — for example:

- domain language and key invariants unique to this codebase
- repo-specific commands (test, lint, deploy) and their gotchas
- areas of the code that have non-obvious constraints
- people, teams, or stakeholders to coordinate with for certain changes

Anything not listed here falls through to `_base/AGENTS.md`.

## Per-directory overrides (monorepos)

For monorepos, place an `AGENTS.md` in any subdirectory to override or extend the root contract for that area. Subdirectory files should reference the root contract (this file + `_base/AGENTS.md`) and specify only what differs. Supported by Claude Code; Codex reads only the root `AGENTS.md`.
