# Central Artifact Registry Plan

## Status

- State: complete
- Execution base revision: `6dc3f5d`
- Repo policy: `.config/repos.project.md` is absent; `origin/master` is the default branch and the
  checkout is on `master`, so this follows the default-branch fallback from `_base/AGENTS.md`.

## Normalized Phase

### Phase 1: Document central artifact registry

Acceptance criteria:

- `artifacts/README.md` is the single discovery point for large, external, generated, encrypted, or
  reproducible artifacts.
- The registry table includes slug, backend, repo path/pattern, purpose, encrypted status, key path,
  fetch command, verify command/checksum, and update notes.
- Git LFS usage is documented with `git lfs install`, `git lfs pull --include="<path-or-pattern>"`,
  `git lfs track "<path-or-pattern>"`, and `git lfs ls-files --name-only`.
- Encryption guidance uses `age`, `.creds/lfs/<artifact-slug>.agekey`, committed `*.age` files, and
  ignored `.local/artifacts/<artifact-slug>/` plaintext outputs.
- `AGENTS.md` and `README.md` point agents and humans to `artifacts/README.md`.
- `.gitattributes` guidance keeps future LFS patterns narrow, per-artifact, and outside the managed
  agents-template block.

Checks:

- `git diff --check`
- Content checks confirming the required files mention the central registry and required Git
  LFS/encryption commands.
- `git lfs ls-files --name-only` to verify the registry has no unlisted current LFS files.

## Architecture Review

Main-thread fallback review, not an independent subagent review: subagent tools are available in this
session, but their usage policy only allows delegation when the user explicitly asks for it.

Verdict: proceed.

Notes:

- Keep `_base/` untouched because it is upstream-owned.
- Do not add broad LFS patterns or placeholder LFS tracking; the repo has no actual artifacts yet.
- Use `artifacts/README.md` for detailed artifact operations and keep root docs as pointers to avoid
  divergent instructions.

## Execution Log

- 2026-06-16: Normalized pasted plan into one documentation phase. Confirmed worktree was clean,
  `.config/repos.project.md` was absent, current/default branch was `master`, no existing root
  `artifacts/` tree existed, and `git lfs ls-files --name-only` returned no tracked files.
- 2026-06-16: Added `artifacts/README.md`, root documentation pointers, downstream-owned
  `artifacts/**` merge handling, and `.gitattributes` placement guidance. Ran `git diff --check`
  (pass), `git lfs ls-files --name-only` (pass, no tracked files), and targeted content checks for
  registry/LFS/encryption terms (pass). Ran `_base/scripts/setup-template-merge-rules.sh --check`
  (pass).

## Final Review

Main-thread fallback review, not an independent subagent review.

Result: pass with one non-blocking process note. The implementation satisfies the normalized
acceptance criteria and keeps `_base/` untouched. Independent subagent review was not run because this
session's subagent tool policy requires explicit user delegation.
