# Human-Reusable Workflow Artifacts Plan

## Status

- State: in progress
- Execution base revision: `e41d907`
- Repo policy: `.config/repos.project.md` is absent; `origin/master` is the default branch and the
  checkout is on `master`, so this follows the default-branch fallback from `_base/AGENTS.md`.
- Effective autonomy: L1 local development. Runtime policy allows local edits, checks, and commits;
  no push, connector write, merge, release, or destructive history action is in scope.

## Normalized Phases

### Phase 1: Add the inherited base-contract rule

Acceptance criteria:

- `_base/AGENTS.md` requires agents to preserve substantial, repeatable, expensive, or
  human-reusable workflow work as repo files instead of leaving it only in inline shell or Python.
- The routing rule is explicit:
  - reusable workflow bundles with scripts/support files go in `workbooks/<workflow-slug>/`
  - stable operational procedures go in `docs/resources/<area>/runbooks/`
  - repo-level Python tooling dependencies go through `tools/python/` and `uv`
  - large, generated, encrypted, external, or reproducible artifacts are registered in
    `artifacts/README.md`
  - tiny inspections, quick grep or JSON parsing, and throwaway feasibility checks may stay inline
- `_base/README.md` makes the rule discoverable from the docs layout and gives model training as an
  example that should become a workbook with scripts and README methodology.

Checks:

- Targeted `rg` checks for `human-runnable`, `inline`, `workbooks/<workflow-slug>`, `runbooks`,
  `tools/python`, `artifacts/README.md`, and `model training`.

### Phase 2: Strengthen workbook conventions

Acceptance criteria:

- `playbooks/conventions/workbook-convention.md` and `_base/workbooks/README.md` define the default
  workbook organization as `README.md`, `scripts/` entrypoints, optional `configs/`, sample inputs,
  documented outputs, support files, and explicit cleanup notes.
- Script expectations are documented: descriptive filenames, runnable commands, arguments/configs,
  expected inputs and outputs, no private local paths or secrets, and methodology captured in the
  workbook README.
- The convention remains distinct from runbooks, resource attachments, generated reports, and the
  artifact registry.

Checks:

- Targeted `rg` checks for `scripts/`, `configs/`, `sample inputs`, `documented outputs`,
  `cleanup`, `arguments`, `private local paths`, and `methodology`.

### Phase 3: Record doctrine refresh and downstream impact

Acceptance criteria:

- `_base/CHANGELOG.md` records the behavior change under Unreleased with a downstream impact note.
- `playbooks/meta/RESEARCH_SNAPSHOT.md` records the added conclusion and source traceability for
  reusable, documented tools/workflow artifacts.
- `playbooks/meta/UPDATE_PLAN.md` records that changing this doctrine requires the refresh loop.
- No automated validator is added in v1.

Checks:

- `git diff --check`
- `./_base/scripts/check-template-update.sh`
- Manual grep for `workbook`, `runbook`, `inline`, and `human-runnable`
- User-scenario review: "agent trains a model" routes to `workbooks/<training-slug>/scripts/*.py`
  plus README methodology and usage.

## Architecture Review

Main-thread fallback review, not an independent subagent review: subagent tools are available in this
session, but their usage policy only allows delegation when the user explicitly asks for subagents.

Verdict: proceed.

Notes:

- The rule belongs in `_base/AGENTS.md` because it is inherited agent behavior, not a
  downstream-owned project override.
- Keep the first version docs-first. Do not add a validator for detecting inline snippets because
  that would be brittle and likely noisy.
- Reuse the existing lanes instead of creating another artifact class: workbooks for reusable bundles,
  runbooks for stable operations, tools/python for persistent Python tooling, and the artifact
  registry for large/generated/reproducible artifacts.
- Update the research snapshot because `_base/AGENTS.md` doctrine is changing and the existing update
  plan requires source traceability for core behavior changes.

## Execution Log

- 2026-06-17: Normalized the pasted plan into three documentation phases. Confirmed worktree was
  clean, `PROJECT.md` and `.config/repos.project.md` were absent, current/default branch was
  `master`, and base revision was `e41d907`. Verified external evidence anchors from Anthropic and
  OpenAI official pages before editing.
- 2026-06-17: Phase 1 in progress. Added the inherited base-contract rule for human-runnable workflow
  artifacts and README discovery guidance, including model training as the concrete workbook routing
  example.
- 2026-06-17: Phase 1 complete. Ran targeted `rg` checks for the required routing/discovery terms
  (pass) and `git diff --check` (pass).
- 2026-06-17: Phase 2 in progress. Strengthened the workbook convention and seed workbook index with
  the default `README.md` plus `scripts/`, optional `configs/`, samples, outputs, support files,
  script expectations, methodology, and cleanup guidance.
- 2026-06-17: Phase 2 complete. Ran targeted `rg` checks for workbook layout/script expectation terms
  (pass) and `git diff --check` (pass).
