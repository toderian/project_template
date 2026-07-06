# Safe Workspace Commit Squash Skill Plan

## Status

- State: complete
- Execution base revision: `c270b22`
- Repo policy: `.config/repos.project.md` is absent; `origin/master` is the configured upstream for
  `master`, and the checkout is on `master`, so this follows the default-branch fallback from
  `_base/AGENTS.md`.
- Alignment note: `/align` could not run because this template repo has no `PROJECT.md`; this plan is
  treated as the source of approved user intent.

## Normalized Phase

### Phase 1: Add safe workspace commit squash skill

Acceptance criteria:

- A new active productivity skill named `squash-workspace-commits` exists in the shared playbook,
  Codex wrapper, Claude wrapper, generated Antigravity wrapper, and `.claude-plugin/plugin.json`.
- The skill description uses the requested trigger phrases and the wrappers remain thin and synced.
- The shared playbook is the canonical workflow for compacting completed workspace/task commits after
  validation while protecting unrelated and pushed/shared history.
- The playbook documents the safe auto-squash policy for contiguous task commits at `HEAD`, interleaved
  path-disjoint unrelated commits, pushed/shared commits, required backup refs, and final commit-message
  preservation.
- `audit-range.py` is an audit-only helper with the CLI
  `python3 .../audit-range.py [--task-id TASK] [--base REF] [--head REF] [--select SHA]... [--json]`.
- The helper reports dirty worktree state, candidate range, selected task commits, unrelated commits,
  pushed/shared commits, merge commits, path overlap, and whether auto-squash is allowed.
- `execute-plan`, `complete-task`, and `_base/AGENTS.md` route optional post-validation squashing through
  the new skill instead of duplicating detailed rules.
- `_base/README.md` and `.agents/skills/...` generated outputs are current.

Checks:

- `_base/scripts/check-skills-sync.sh`
- `_base/scripts/gen-skills-table.sh --check`
- `_base/scripts/gen-antigravity-skills.sh --check`
- `_base/scripts/check-antigravity-skills.sh`
- `git diff --check`
- Temporary git repo scenarios for `audit-range.py`:
  - contiguous unpushed task commits allow `soft-reset`
  - mixed task/unrelated commits with disjoint paths allow `mixed-rewrite`
  - dirty worktree blocks auto-squash
  - pushed/shared commit in range blocks by default
  - merge commit in range blocks auto-squash
  - ambiguous task with no base/selected SHAs asks for explicit range/selection

## Architecture Review

Main-thread fallback review, not an independent subagent review: this runtime exposes subagent tooling
only when the user explicitly asks for delegation, and the user did not request subagents.

Verdict: proceed.

Notes:

- Keep the helper audit-only; no `reset`, `rebase`, `commit`, `cherry-pick`, or ref updates belong in
  the script.
- Preserve the repo's manifest-driven skill model: update shared playbook first, then thin wrappers,
  then generated `.agents/skills` and `_base/README.md`.
- Favor conservative refusal. The helper can report an allowed plan only when commit identity, dirty
  state, pushed/shared status, merge status, and path overlap all support an automatic workflow.

## Execution Log

- 2026-06-16: Normalized the pasted plan into one cohesive implementation phase. Confirmed the worktree
  was clean, `.config/repos.project.md` was absent, current branch was `master`, and base revision was
  `c270b22`. `/align` could not run because `PROJECT.md` is absent.
- 2026-06-16: Added the `squash-workspace-commits` productivity skill, thin Codex and Claude wrappers,
  manifest entry, generated Antigravity wrapper, generated README skill table row, and routed
  `execute-plan`, `complete-task`, and `_base/AGENTS.md` to the new canonical workflow.
- 2026-06-16: Added the read-only `audit-range.py` helper. It reports dirty state, selected and
  unrelated commits, pushed/shared commits from local remote-tracking refs, merge commits, path overlap,
  and the safe auto-squash method when available.
- 2026-06-16: Tightened path-overlap detection to account for rename/copy name-status entries. Ran
  `_base/scripts/check-skills-sync.sh` (pass), `_base/scripts/gen-skills-table.sh --check` (pass),
  `_base/scripts/gen-antigravity-skills.sh --check` (pass),
  `_base/scripts/check-antigravity-skills.sh` (pass), and `git diff --check` (pass).
- 2026-06-16: Exercised `audit-range.py` in temporary Git repositories: contiguous unpushed task
  commits allowed `soft-reset`; mixed task/unrelated disjoint commits allowed `mixed-rewrite`; dirty
  worktree blocked; pushed/shared commit blocked; merge commit blocked; ambiguous no-base/no-selection
  case asked for explicit range/selection; overlapping interleaved paths blocked. Also ran
  `python3 -m py_compile` on the helper (pass).

## Final Review

Main-thread fallback review, not an independent subagent review: this runtime exposes subagent tooling
only when the user explicitly asks for delegation, and the user did not request subagents.

Result: pass with one residual implementation note. The helper's pushed/shared detection is based on
local remote-tracking refs and intentionally does not fetch remotes because the helper is audit-only.
The playbook still requires refusal whenever pushed/shared status is uncertain.
