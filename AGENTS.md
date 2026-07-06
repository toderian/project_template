# AGENTS.md

> **Auto-loaded entrypoint for the agent operating contract.** Both Claude Code and Codex load this file automatically at session start.
>
> **First instruction to every agent:** before acting, read the **Start here (tier 0)** section of [`_base/AGENTS.md`](./_base/AGENTS.md) and follow its routing table — load the deeper sections and conventions it lists only as your current task requires. `_base/AGENTS.md` is the authoritative base contract; this `AGENTS.md` is the downstream-owned entrypoint that may add project-specific overrides below. Treat the two files as a single contract, with overrides in this file taking precedence over the base.

## How this file is structured

This is the **base template's** `AGENTS.md`. It is intentionally small and contains only the
downstream-owned conventions that should seed new projects.

When this template is seeded into a new project:

- `_base/AGENTS.md` is **upstream-owned**: do not edit it downstream. It updates cleanly via `git fetch template && git merge`.
- `AGENTS.md` (this file) is **downstream-owned**: each project replaces or extends the
  "Project-specific overrides" section below with its own rules. Future template improvements to
  `AGENTS.md` will be rare; when they happen, downstream projects merge by hand.

## Project-specific overrides

### Implementation footprint

- Prefer a minimal code footprint with maximal high-signal documentation. Change the smallest code
  surface that satisfies the current objective, then document behavior, rationale, constraints, and
  verification clearly enough that future agents do not need to infer intent from extra scaffolding.
- Make surgical modifications in existing modules and patterns. Add code only for a present bug,
  current requirement, or explicitly requested capability.
- Do not add abstractions, extension points, configuration layers, generated helpers, or
  "future-proof" modules for imaginary future use cases. Capture deferred possibilities in docs,
  tasks, or comments instead of executable code.
- When intent, tradeoffs, or deferred options do not need to execute, prefer documentation over more
  code. Code should embody current behavior; documentation should carry context.

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

### Artifact registry

- Large, external, generated, encrypted, or reproducible artifacts must be discoverable through
  [`artifacts/README.md`](./artifacts/README.md). Before walking the repository for artifacts, read
  that registry for the artifact slug, backend, path or pattern, fetch command, verification command,
  encryption status, and update notes.
- Use `artifacts/lfs/<artifact-slug>/` as the default home for new Git LFS-managed artifacts. Files
  may live elsewhere only when colocating with source, docs, or tests is materially clearer, and they
  must still be listed in `artifacts/README.md`.
- Before using Git LFS artifacts, run `git lfs install`, then fetch only the needed registry entries
  with `git lfs pull --include="<path-or-pattern>"`. Verify registry drift with
  `git lfs ls-files --name-only` and confirm every tracked path is represented in
  `artifacts/README.md`.
- Before committing new Git LFS artifacts, run `git lfs track "<path-or-pattern>"`, keep the
  `.gitattributes` LFS pattern narrow and per-artifact, and place project-specific LFS rules outside
  the managed agents-template block, preferably after `# END agents-template merge rules`. Commit the
  updated `.gitattributes` and the `artifacts/README.md` registry entry in the same change.
- For encrypted artifacts, use `age` by default. Commit only encrypted files such as `*.age` through
  Git LFS, store private keys under `.creds/lfs/<artifact-slug>.agekey`, and keep decrypted outputs
  under ignored local paths such as `.local/artifacts/<artifact-slug>/`. Never print, summarize, or
  commit private keys or plaintext secrets.

### Python tooling environments

- Use `uv` (not `pip install`) for persistent repo-level Python tooling, kept under `tools/python/`
  rather than the repo root. The authoritative rules — committed `pyproject.toml`/`uv.lock`/
  `.python-version`, the local-only `.venv/`, running commands from `tools/python/`, multi-environment
  layout, and not creating metadata files before real dependencies exist — live in
  [`_base/AGENTS.md`](./_base/AGENTS.md) → "Python tooling environment". Add project-specific tooling
  notes here only when they differ from that base rule.

Downstream projects, replace or extend this section with rules that are specific to your project — for example:

- domain language and key invariants unique to this codebase
- repo-specific commands (test, lint, deploy) and their gotchas
- areas of the code that have non-obvious constraints
- people, teams, or stakeholders to coordinate with for certain changes

Anything not listed here falls through to `_base/AGENTS.md`.

## Per-directory overrides (monorepos)

For monorepos, place an `AGENTS.md` in any subdirectory to override or extend the root contract for that area. Subdirectory files should reference the root contract (this file + `_base/AGENTS.md`) and specify only what differs. Supported by Claude Code; Codex reads only the root `AGENTS.md`.
