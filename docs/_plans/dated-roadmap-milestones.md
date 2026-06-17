# Dated Roadmap Milestones Plan

## Status

- State: in progress
- Execution base revision: `c50a212`
- Repo policy: `.config/repos.project.md` is absent; the checkout is on `master`, so this follows the
  default-branch fallback from `_base/AGENTS.md`.
- Alignment note: `/align` could not run because this template repo has no root `PROJECT.md`; this
  pasted plan is treated as the approved user intent.

## Normalized Phases

### Phase 1: Document dated roadmap milestones and optional task dates

Acceptance criteria:

- Roadmap conventions keep `Urgent`, `Now`, `Next`, `Later`, and `Someday` as the only top-level
  execution horizons.
- Roadmap milestones are documented as `### Milestone: <name> (target: YYYY-MM-DD)` or
  `### Milestone: <name> (deadline: YYYY-MM-DD)` headings nested under existing horizons.
- Task metadata documents optional `Target date` and `Deadline` rows, each accepting `YYYY-MM-DD` or
  `N/A`.
- Task creation and triage skills ask for dates only when the user explicitly expresses scheduling
  intent; normal task creation stays undated by default.

Checks:

- `git diff --check`
- `_base/scripts/check-skills-sync.sh`
- `_base/scripts/gen-skills-table.sh --check`
- `_base/scripts/gen-antigravity-skills.sh --check`
- `_base/scripts/check-antigravity-skills.sh`

### Phase 2: Validate milestone and task date syntax in sync tooling

Acceptance criteria:

- `_base/scripts/sync-todo-ledgers.sh --check` accepts seeded roadmaps with no milestones.
- Valid milestone headings still assign task IDs to their containing horizon.
- Malformed milestone headings or dates produce validation warnings/errors in check mode.
- Optional task `Target date` and `Deadline` metadata accepts `YYYY-MM-DD` or `N/A`.
- Existing roadmap validation behavior remains intact for missing task IDs, duplicate task IDs, and
  inbox IDs outside `Someday`.

Checks:

- `bash -n _base/scripts/sync-todo-ledgers.sh`
- `_base/scripts/sync-todo-ledgers.sh --check`
- Temporary fixture checks covering no milestones, valid milestones, malformed milestone dates,
  optional task dates, missing roadmap task IDs, duplicate task IDs, and inbox IDs outside `Someday`.
- `git diff --check`

## Architecture Review

Main-thread fallback review, not an independent subagent review: this runtime exposes subagent tooling
only when the user explicitly asks for delegation, and the user did not request subagents.

Verdict: proceed.

Notes:

- Keep milestone support inside existing horizons; do not add a generated milestone ledger or a new
  top-level roadmap section.
- Preserve the current roadmap scan shape so task and inbox ID reference validation remains unchanged.
- Treat `Target date` and `Deadline` as optional metadata only; task creation workflows should not ask
  for them unless the user provides or asks for scheduling.

## Execution Log

- 2026-06-17T12:15:55+0300: Normalized the pasted plan into two implementation phases. Confirmed the
  worktree was clean, `.config/repos.project.md` was absent, current branch was `master`, and base
  revision was `c50a212`. `/align` could not run because `PROJECT.md` is absent. Baseline
  `_base/scripts/sync-todo-ledgers.sh --check` exited 0 with no initialized `docs/tasks_manager/`
  directory in this template repo.
- 2026-06-17T12:21:04+0300: Phase 1 documented roadmap-level milestone headings, optional
  task-specific `Target date` / `Deadline` metadata, and scheduling-date prompts only when user intent
  is explicit. Regenerated Antigravity wrappers and the `_base/README.md` skill table. Checks passed:
  `git diff --check`, `_base/scripts/check-skills-sync.sh`, `_base/scripts/gen-skills-table.sh --check`,
  `_base/scripts/gen-antigravity-skills.sh --check`, and `_base/scripts/check-antigravity-skills.sh`.

## Final Review

Pending.
