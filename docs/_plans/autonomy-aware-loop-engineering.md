# Autonomy-Aware Loop Engineering Adoption Plan

## Status

- State: in_progress
- Execution base revision: `0617475`
- Repo policy: `.config/repos.project.md` is absent; `origin/master` is the configured upstream for
  `master`, and the checkout is on `master`, so this follows the default-branch fallback from
  `_base/AGENTS.md`.
- Alignment note: `/align` could not run because this template repo has no `PROJECT.md`; this plan is
  treated as the source of approved user intent.
- Review note: subagent tooling is available in this runtime, but the tool contract only permits
  spawning subagents when the user explicitly asks for delegation or parallel agent work. Architecture
  and final reviews in this run are documented main-thread fallback reviews.

## Normalized Phases

### Phase 1: Research and doctrine

Acceptance criteria:

- `_base/docs/resources/_digests/global/2026-06-17-loop-engineering-digest.md` records the external
  loop-engineering source in a copyright-safe, source-traceable form.
- `playbooks/conventions/autonomy-levels.md` defines L0 through L3 as a permission ceiling layered on
  existing branch/work rules.
- The convention defines precedence: hard safety/runtime permissions, repo `Work mode`, branch
  resolution, repo `Autonomy max`, then task `Autonomy`; strictest rule wins.
- `_base/README.md`, `_base/CHANGELOG.md`, and `playbooks/meta/RESEARCH_SNAPSHOT.md` reference the
  new doctrine.

Checks:

- `git diff --check`
- manual copyright/source review of the digest

### Phase 2: Registry and task schema

Acceptance criteria:

- `_base/repos.project.example.md`, `todo-convention.md`, task-system docs, setup docs, and
  task-producing playbooks document optional `Autonomy max` and task `Autonomy`.
- Existing 8-column repo registries remain valid and default to L1.
- New 9-column repo registries with `Autonomy max` validate.
- Optional task `Autonomy` values validate against allowed autonomy levels and cannot silently exceed
  the repo maximum.
- Migration guidance says downstream-owned `.config/repos.project.md` files are not rewritten
  automatically.

Checks:

- `_base/scripts/check-repos-config.sh` valid/invalid fixtures for old registry, new registry, invalid
  autonomy values, and task `Autonomy` below/equal/above repo max.
- `bash -n _base/scripts/check-repos-config.sh`
- `git diff --check`

### Phase 3: Execution and publishing gates

Acceptance criteria:

- `execute-plan` resolves and logs effective autonomy before edits.
- GitHub publish and CI repair workflows require explicit L2/L3 opt-in gates instead of treating
  branch metadata as automatic push/PR permission.
- L2 push/CI behavior is constrained to the branch allowed by repo work mode.
- L3 opens or updates draft PRs only and stops before ready-for-review, merge, deploy, release, or
  force-push/rewrite behavior.

Checks:

- targeted documentation searches for L2/L3 push and draft PR gating
- `git diff --check`

### Phase 4: Loop recipes and isolation

Acceptance criteria:

- `playbooks/conventions/agent-loop-recipes.md` documents compact loop recipe fields: recipe, minimum
  autonomy, required work mode, workspace mode, allowed stop point, and must-ask-before.
- Examples cover L0 audits, L1 local implementation, L2 CI repair, and L3 draft PR validation.
- Worktree isolation guidance is documented.
- `.worktrees/` and `worktrees/` are ignored.

Checks:

- `git check-ignore .worktrees/example worktrees/example`
- `git diff --check`

### Phase 5: Connectors and Codex agent mirrors

Acceptance criteria:

- `playbooks/conventions/connectors-and-mcp.md` documents least-privilege connector/MCP behavior by
  autonomy level, including private/live data and secret handling.
- `.codex/agents/*.toml` contains thin project-scoped Codex agent mirrors that point at existing
  playbooks and personality rules without duplicating workflow logic.
- Local Codex config/state remains ignored while intended `.codex/agents/*.toml` files are trackable.
- Validation catches tracked `.codex` files outside the intended agent mirrors.

Checks:

- `.codex/config.toml` is ignored.
- `.codex/agents/reviewer.toml` is trackable.
- New Codex-agent validation passes.
- `./_base/scripts/check-template-update.sh`
- `bash -n` on changed shell scripts.
- `_base/scripts/check-skills-sync.sh`
- `_base/scripts/check-antigravity-skills.sh`
- `_base/scripts/check-codex-plugins.sh`
- `_base/scripts/setup-template-merge-rules.sh --check`
- `git diff --check`

## Architecture Review

Main-thread fallback review, not an independent subagent review.

Verdict: proceed with constraints.

Notes:

- The autonomy ladder must be a permission ceiling, not a new branch model. Existing `Work mode`
  semantics continue to decide where edits happen; autonomy only decides how far an agent may proceed
  after edits and checks.
- The highest-risk ambiguity is publish consent. L2/L3 can authorize a loop shape only when repo/task
  metadata or the user explicitly opts into that level; it does not override the base rule that direct
  user instruction, runtime permissions, and safety gates can be stricter.
- Keep downstream registries backward-compatible. Treat the 8-column table as valid and default its
  repo autonomy maximum to L1.
- Keep task-level `Autonomy` optional and conservative. Omitted uses the repo ceiling; a lower task
  value lowers the effective ceiling; a higher task value must be explicit escalation and cannot pass
  validation when it exceeds the repo max.
- Keep Codex agent mirrors thin. Project-scoped `.codex/agents/*.toml` files may point at existing
  playbooks and role cards, but workflow logic remains in `playbooks/`.

## Execution Log

- 2026-06-17T10:42:57+03:00: Normalized the pasted implementation plan into this durable plan file.
  Confirmed the worktree was clean, `.config/repos.project.md` was absent, current branch was `master`,
  and base revision was `0617475`. `/align` could not run because `PROJECT.md` is absent. The
  OpenAI Codex manual was fetched through the `openai-docs` skill helper for current project-scoped
  custom-agent file format details.
- 2026-06-17T10:42:57+03:00: Phase 1 added the autonomy-level convention, loop-engineering digest,
  research snapshot entry, changelog entry, and README pointer. `git diff --check` passed. Manual
  digest review found only paraphrase plus source metadata, with no long copied article excerpts.
- 2026-06-17T10:42:57+03:00: Phase 2 updated the repo registry and task metadata conventions,
  setup/quickstart docs, task-producing playbooks, and `_base/scripts/check-repos-config.sh`.
  Validator fixture checks passed for old 8-column registries, new registries with `Autonomy max`,
  invalid registry autonomy values, task autonomy below/equal repo max, and task autonomy above repo
  max. `bash -n _base/scripts/check-repos-config.sh`, `_base/scripts/check-repos-config.sh`, and
  `git diff --check` passed.
