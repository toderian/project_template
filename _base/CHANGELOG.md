# Changelog (base)

> This is `_base/CHANGELOG.md`: the changelog for **base-template** changes only.
> Downstream projects may keep their own `CHANGELOG.md` for changes they make on top of the template; the two files never overlap.

All template-relevant changes are recorded here so downstream projects can see what's coming in before running `git merge template/master`.

Format: reverse chronological. Each entry lists the date, a short description, and (where relevant) a **Downstream impact** line explaining what a project pulling this in should expect — particularly merge conflicts, new conventions to follow, or behavior changes.

This file is **upstream-owned**: do not edit it in a downstream project. It updates cleanly via `git fetch template && git merge`.

For exhaustive history, use `git log` against the `template` remote.

## Unreleased

### Add `plugins/install-claude-plugins.sh` and `_base/SETUP_INSTRUCTIONS.md`

Two related additions that close the dual-runtime setup story for downstream projects.

- **`plugins/install-claude-plugins.sh`** — installs a curated set of Claude Code plugins by merging entries into `~/.claude/settings.json` (`extraKnownMarketplaces` + `enabledPlugins`). Idempotent: re-running reports `already present, left as-is` for entries that already exist; preserves unrelated keys in the user's settings. The curated default list is hard-coded at the top of the script under `PLUGINS=( … )` and is easy to edit. The list ships with two starters: `obra/superpowers` (Claude variant of the already-vendored Codex superpowers plugin) and `thedotmack/claude-mem` (cross-session memory). No umbrella `install-all.sh` — installers stay agent-scoped (Codex installers under `skills/` + `plugins/`; Claude installer under `plugins/`).
- **`_base/SETUP_INSTRUCTIONS.md`** — agent-readable numbered setup steps for wiring up a fresh project. **Each agent sets up only its own runtime**: Claude Code agents run Phases 0–2 + Phase 3 (Claude) + Phases 5–6; Codex agents run Phases 0–2 + Phase 4 (Codex) + Phases 5–6. Phases 0, 1, 2, 5, 6 are idempotent, so a second agent on the other runtime can re-run the file later to set up its side without re-doing or breaking the first agent's work. Each step has an explicit check; on any failure the agent stops and hands control back to the user. Pointed at like `Follow _base/SETUP_INSTRUCTIONS.md`.

**Downstream impact:** none for existing projects; the new installer is opt-in. Newly-seeded projects benefit immediately — pointing an agent at `_base/SETUP_INSTRUCTIONS.md` is now the canonical setup path (`_base/README.md` § "Quick start" updated to reflect this). The file ownership matrix in both `_base/README.md` and `_base/AGENTS.md` now lists `_base/SETUP_INSTRUCTIONS.md` as upstream-owned.

### Add `spec-workflow` skill

New heavyweight skill that drives a plan → build → review → fix loop for a single engineering item, with four standardized artifacts under `specs/<slug>/` (`spec.md`, `design.md`, `tasks.md`, `review.md`). Reuses the existing `subagent-protocol` dispatch + status vocabulary and the existing `implementer` and `reviewer` subagent/skill definitions — no new agent definitions, no experimental flags. Runtime-agnostic: same playbook and artifacts on Claude Code (Task-tool parallel dispatch) and Codex (sequential `/implementer` invocation per task). Composes with the existing PRD chain — `write-a-prd` / `prd-to-plan` / `prd-to-issues` / `prd-to-todos` remain unchanged; spec-workflow accepts a PRD or rough intent as input. Strong "do NOT use for…" guardrails in the wrapper description keep it from auto-triggering on small tasks.

**Downstream impact:** none. New skill; opt-in by invocation. After merging, run `./scripts/gen-skills-table.sh` to regenerate the skills table in this file's sibling `_base/README.md`. No conflicts expected; new files only.

## 2026-05-11

### Add `scripts/gen-skills-table.sh` and `_base/CHANGELOG.md`

The "Available skills" table in `_base/README.md` is now auto-generated from `playbooks/skills/*.md` between `<!-- BEGIN skills-table -->` / `<!-- END skills-table -->` markers. Run `./scripts/gen-skills-table.sh` after adding, renaming, or removing a skill. Descriptions are pulled from the matching Claude wrapper's `description:` frontmatter (falls back to the playbook's `## Purpose` paragraph).

This base-changelog file (`_base/CHANGELOG.md`) was added. It lives under `_base/` alongside the other upstream-owned files, so a downstream project can keep its own root-level `CHANGELOG.md` without collision.

**Downstream impact:** none. Upstream-owned file; no manual action required after `git merge`. Downstream projects may keep a separate root-level `CHANGELOG.md` for their own changes.

### Split `AGENTS.md` and `README.md` into entrypoints + `_base/` files

Established a template-remote convention. New upstream-owned `_base/` directory at the repo root, containing:

- `_base/AGENTS.md` — base operating contract (previously the entirety of `AGENTS.md`).
- `_base/README.md` — base documentation (previously the entirety of `README.md`).

The remaining root-level `AGENTS.md` and `README.md` are now **downstream-owned**:

- `AGENTS.md` is a short auto-loaded entrypoint that instructs agents to also read `_base/AGENTS.md` and applies any project-specific overrides on top.
- `README.md` is the downstream project's own README; it links to `_base/README.md`.

Simple rule for merge conflicts going forward: always accept upstream under `_base/*`; keep downstream for `AGENTS.md`, `README.md`, and any customized skills.

**Downstream impact (one-time merge, expected to be small):**

- On first pull after this change, you'll see a new `_base/` directory appear. Accept it as-is from upstream.
- Your existing `AGENTS.md` and `README.md` may conflict with the new short entrypoint versions. **Default to keeping your downstream content** — your `AGENTS.md` already contains your project rules, and your `README.md` already describes your project. Lift the "First instruction to every agent: also read `_base/AGENTS.md`" directive into the top of your `AGENTS.md` so agents continue to load the base contract.
- After this one-time merge, future template pulls will not conflict on `AGENTS.md` or `README.md`.

### `template` git remote convention

Every project seeded from this template should keep a fetch-only `template` remote pointing at `git@github.com:toderian/project_template.git`. Documented in `_base/README.md` → "Staying in sync with the template" and `_base/AGENTS.md` → "Template-remote convention".

**Downstream impact:** if your project was started by copying files (not cloning), add the remote retroactively:

```bash
git remote add template git@github.com:toderian/project_template.git
git remote set-url --push template DISABLE
git fetch template
```

## 2026-05-10

### Add OWASP and migration-safety skills; harden bash hook

- New skill `security-review-owasp` (vendored from `agamm/claude-code-owasp`): applies OWASP Top 10:2025, ASVS 5.0, LLM Top 10 2025, and Agentic AI 2026.
- New skill `migration-safety` (adapted from OmexIT): generates safe, reversible DB schema migrations and reviews proposed ones for production hazards. Default focus PostgreSQL with Liquibase/Flyway.
- `.claude/hooks/block-dangerous-bash.sh` hardened against more dangerous shell invocations.

**Downstream impact:** the two new skills are additive and opt-in. The hook change tightens an existing block — review your hook config if you've customized it.

### Dual-runtime audit fixes

Closed gaps between Claude Code and Codex wrappers across existing skills so both runtimes get equivalent behavior.

**Downstream impact:** none expected unless you've forked specific wrappers.

### Add frontend-design skill, third-party bootstrap, richer write-a-skill

- New skill `frontend-design` (imported from Anthropic's frontend-design plugin): builds distinctive, production-grade frontend interfaces.
- `plugins/bootstrap-third-party.sh` installs/documents third-party tools (`get-shit-done-cc`, `context-mode`, `claude-mem`) that ship their own multi-platform installers. Toggle each with env vars (`INSTALL_GSD`, `INSTALL_CONTEXT_MODE`, `INSTALL_CLAUDE_MEM`).
- `write-a-skill` playbook expanded with more concrete guidance.

**Downstream impact:** additive. To pick up the third-party tools, run `./plugins/bootstrap-third-party.sh`.

## 2026-04-27

### Bundle GitHub Codex plugin and add Codex plugin installation support

- New `plugins/install-codex-plugins.sh` symlinks repo plugins into `~/plugins/` and adds local marketplace entries to `~/.agents/plugins/marketplace.json`.
- Vendored `plugins/github/` plugin for Codex (PR/issue/CI workflows).

**Downstream impact:** additive. Run `./plugins/install-codex-plugins.sh` if you use Codex; restart Codex after.

## 2026-04-14

### Add todo-tracking skills with phased execution convention

New `init`, `prd-to-todos`, and related skills introduce a `docs/_todos/` + `_todos_archived/` convention for durable task tracking.

**Downstream impact:** additive. The convention only applies if you invoke `/init` or the related skills.

## 2026-04-09

### Reorganize: skill playbooks moved to `playbooks/skills/`

Authoritative skill workflow logic now lives under `playbooks/skills/<name>.md`. `skills/<name>/SKILL.md` (Codex) and `.claude/skills/<name>/SKILL.md` (Claude Code) are thin wrappers that point to the playbook.

**Downstream impact:** if you forked any skill, ensure your fork follows the new layout — the playbook is the single source of truth; both wrappers should be thin and reference it. The `install-codex-skills.sh` script also moved from `scripts/` to `skills/`.

### Add `project.env.example`

Copy to `project.env` to override default install paths for the Codex installers.

**Downstream impact:** optional. Defaults still work without it.

## Earlier history

Pre-2026-04-09 changes are not catalogued here. Use `git log` for full history.
