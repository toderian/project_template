# Changelog (base)

> This is `_base/CHANGELOG.md`: the changelog for **base-template** changes only.
> Downstream projects may keep their own `CHANGELOG.md` for changes they make on top of the template; the two files never overlap.

All template-relevant changes are recorded here so downstream projects can see what's coming in before running `git merge template/master`.

Format: reverse chronological. Each entry lists the date, a short description, and (where relevant) a **Downstream impact** line explaining what a project pulling this in should expect — particularly merge conflicts, new conventions to follow, or behavior changes.

This file is **upstream-owned**: do not edit it in a downstream project. It updates cleanly via `git fetch template && git merge`.

For exhaustive history, use `git log` against the `template` remote.

## Unreleased

### Add `test-taxonomy` convention naming the five test layers

New `playbooks/conventions/test-taxonomy.md` names the five layers this template recognizes — acceptance, contract, property-based, integration, unit — with definitions, when-to-use guidance, example assertion shapes, a decision matrix by change type (utility / data model / API / auth / multi-component / bug fix / UI / refactor), and a failure-modes section. The convention is shared vocabulary, not a workflow.

Existing files gain one-paragraph references:

- `playbooks/skills/tdd.md` — points readers at the taxonomy for the layer vocabulary; the skill itself stays focused on the RGR loop and vertical slices.
- `.claude/agents/spec-validator.md` — notes that the binary pass/fail tests it writes are the acceptance layer of the taxonomy, scoping it away from unit/integration/property-based work.

Neither file is restructured. The taxonomy lives in `playbooks/conventions/` next to `todo-convention.md` and `plan-critique.md`, matching the bare-markdown convention pattern.

**Downstream impact:** new file plus two minimal additions. No conflicts expected. Downstream projects that have customized `tdd.md` will need to merge the new one-paragraph reference by hand. The convention is opt-in — any skill or agent that wants the shared vocabulary can reference it; nothing forces it.

### Add `block-write-sensitive` hook to guard Write/Edit on sensitive paths

New `.claude/hooks/block-write-sensitive.sh` is a `PreToolUse` hook on `Write|Edit|MultiEdit` that denies operations targeting sensitive paths. Patterns blocked: `.env` and `.env.*` files, anything under `.git/`, `credentials`, `secrets`, `private*key`, `*.pem`, `*.key`, `.ssh/`, `.aws/`. Closes the chokepoint that the existing Bash guards (`block-dangerous-bash.sh`, `block-dangerous-git.sh`) don't cover — the Write/Edit tools can otherwise overwrite secrets and git internals without going through a shell.

Matches the existing hook style (stdin → `jq` → exit 2 on block with stderr message, exit 0 on allow). The new matcher entry is appended to `.claude/settings.json` next to the existing Bash matcher; no existing hooks were modified.

**Downstream impact:** new files and a new `PreToolUse.matcher` entry in `.claude/settings.json`. Downstream projects that have customized `.claude/settings.json` will need to merge the new `Write|Edit|MultiEdit` matcher block by hand (the existing `Bash` block is unchanged). If a downstream project has a legitimate reason to write to one of the protected paths (e.g., generating a `.env` from a configurator script), either narrow the patterns in the script or remove it from the matcher list locally — agents that hit the block should ask the user before overriding.

### Add adversarial review and research subagents

Four new Claude Code subagents in `.claude/agents/`, ported from the [autonomous-dev](https://github.com/akaszubski/autonomous-dev) harness and adapted to this template's style and skill graph:

- **`plan-critic`** — adversarial plan review against the five-axis rubric in `playbooks/conventions/plan-critique.md`. Issues PROCEED, REVISE, or BLOCKED with composite scoring. Read-only.
- **`spec-validator`** — spec-blind behavioral validation. Reads only the acceptance criteria (not the implementation), writes binary pass/fail tests in `tests/spec_validation/`, and reports PASS or FAIL.
- **`security-auditor`** — OWASP + LLM + Agentic AI review using the existing `security-review-owasp` skill. Smart secret detection that distinguishes correctly-gitignored `.env` from secrets in source/history. Flags deletion of security-related tests as HIGH.
- **`researcher`** — codebase-first investigation with citation and tradeoff requirements. Pairs with the broadened `researcher` personality.

`_base/AGENTS.md` gains a new "Available subagents" subsection under Multi-agent rules, cataloging all six subagents (the four new ones plus the existing `implementer` and `reviewer`) with purpose and dispatch trigger.

Harness-specific bits from the source were dropped during the port: file-write verdict gates, checkpoint-tracker Python blocks, active-scanner library imports, pipeline-state JSON files, RFC 2119 MUST/SHOULD shouting, and HARD GATE / FORBIDDEN markers. The ported content references this template's existing personalities (`critic`, `reviewer`, `researcher`) and skills (`security-review-owasp`) rather than duplicating their content.

**Downstream impact:** new files only; no conflicts expected. Claude Code users gain four additional subagents discoverable via `.claude/agents/` and the updated catalog in `_base/AGENTS.md`. Codex has no equivalent subagent runtime — `plan-critic`, `spec-validator`, `security-auditor`, and `researcher` must run on the main thread under the cited personality + skill/convention in Codex sessions; only the `planning-workflow` skill (shipped in the previous entry) has full Codex parity.

### Add `planning-workflow` skill and `plan-critique` convention

New methodology for pre-implementation planning:

- **`planning-workflow` skill** (`playbooks/skills/planning-workflow.md` + Codex wrapper at `skills/planning-workflow/` + Claude wrapper at `.claude/skills/planning-workflow/`) — a seven-step pre-implementation workflow: problem statement, scope check (with a 1.5x halt rule), existing-solutions search, minimal-path design, adversarial critique, decomposition, and durable plan output.
- **`plan-critique` convention** (`playbooks/conventions/plan-critique.md`) — a five-axis scoring rubric (assumption audit, scope creep, existing solutions, minimalism, uncertainty) with a fixed composite-to-verdict mapping (≥3.0 / no axis below 2 → PROCEED; <3.0 or any axis at 1 → REVISE; <2.0 or two or more axes at 1 → BLOCKED), calibration anchors per axis, minimum-rounds rule scaled by complexity, and a required output template. Applicable on the main thread under the `critic` personality, and used directly by the new `plan-critic` subagent (forthcoming).

The skills table in `_base/README.md` was regenerated to include `planning-workflow`.

**Downstream impact:** new files only; no conflicts expected. The convention adds a published rubric that existing skills like `prd-to-plan` and the `critic` personality can reference for plan validation. Run `./_base/scripts/gen-skills-table.sh` after merging if your downstream `_base/README.md` skills table is out of date.

### Broaden researcher personality to a general research role

`playbooks/personalities/researcher.md` evolved from a narrow doctrine-refresher into a general research role. New content: a four-phase workflow (codebase recon → targeted search → deep read of authoritative sources → synthesis), an explicit source hierarchy (official docs → reference implementations → community sources), and explicit citation + tradeoff requirements. The original doctrine-refresh use case (refreshing `_base/AGENTS.md` and evaluation guides) is preserved as one application of the broader role.

**Downstream impact:** strict superset of the previous personality — projects relying on the old framing keep working. Any new investigation task can now reference this role for consistent methodology.

### Move `project.env.example` under `_base/`

The reference env-vars file is now at `_base/project.env.example`. The live `project.env` continues to live at the repo root (gitignored) and is the file all four installer scripts (`skills/install-codex-skills.sh`, `plugins/install-codex-plugins.sh`, `plugins/install-claude-plugins.sh`, `plugins/bootstrap-third-party.sh`) source — no installer changes were needed. The example file's internal header comment now documents the new copy command: `cp _base/project.env.example project.env`.

**Downstream impact:** if your downstream `README.md`, scripts, CI, or local notes reference `project.env.example` at the repo root, update the path to `_base/project.env.example` after merging. Your live `project.env` at the repo root is unaffected and continues to work as-is. Future template updates to the reference env vars (new entries, removed entries, comment changes) will now arrive cleanly inside `_base/` instead of as root-level merge candidates. Downstream projects that want to ship their *own* `.env.example` for project-specific env vars can now do so at the repo root without colliding with the template's.

### Move maintenance scripts under `_base/scripts/`

Both `scripts/gen-skills-table.sh` and `scripts/check-skills-sync.sh` now live at `_base/scripts/`. They only operate on upstream-owned content (the auto-generated table in `_base/README.md` and the template's skill catalog), so colocating them with the other `_base/` upstream files makes the ownership boundary explicit and frees the root-level `scripts/` namespace for downstream-owned tooling. The internal `REPO_ROOT` resolution in each script and the auto-generated table comment now point to the new path.

**Downstream impact:** if you have any local automation (CI, git hooks, shell aliases, downstream `AGENTS.md` rules) that invokes `./scripts/gen-skills-table.sh` or `./scripts/check-skills-sync.sh`, update the path to `./_base/scripts/…` after merging. No behavior change otherwise. If your downstream project has its own `scripts/` directory, it now coexists cleanly with the template's maintenance scripts (no merge conflict).

### Add `_base/scripts/check-skills-sync.sh` validator

New maintenance script that validates skill / wrapper / table consistency: every playbook has matching Codex + Claude wrappers, frontmatter `name` matches the directory, descriptions are present, Claude wrappers carry `disable-model-invocation: true`, wrappers reference their playbook and stay thin (≤50 lines), personalities aren't exposed as slash commands, the auto-generated skills table in `_base/README.md` is up-to-date, and quoted trigger phrases (e.g. `"red-green-refactor"`) don't drift between the Codex and Claude wrapper descriptions. Line-oriented output (`SEVERITY<tab>CHECK_ID<tab>PATH<tab>[details]`) with three tiers (BLOCKER / DRIFT / STYLE); exit 1 on BLOCKER or DRIFT, designed to be called by an agent in a loop (run → fix → re-run until clean).

**Downstream impact:** none. Opt-in maintenance script. Recommended after adding or modifying any skill or wrapper, and as a CI gate for downstream projects that add their own skills. The "Adding a new skill" checklist in `_base/README.md` now includes a regenerate-table + validate step.

### Add `plugins/install-claude-plugins.sh` and `_base/SETUP_INSTRUCTIONS.md`

Two related additions that close the dual-runtime setup story for downstream projects.

- **`plugins/install-claude-plugins.sh`** — installs a curated set of Claude Code plugins by merging entries into `~/.claude/settings.json` (`extraKnownMarketplaces` + `enabledPlugins`). Idempotent: re-running reports `already present, left as-is` for entries that already exist; preserves unrelated keys in the user's settings. The curated default list is hard-coded at the top of the script under `PLUGINS=( … )` and is easy to edit. The list ships with two starters: `obra/superpowers` (Claude variant of the already-vendored Codex superpowers plugin) and `thedotmack/claude-mem` (cross-session memory). No umbrella `install-all.sh` — installers stay agent-scoped (Codex installers under `skills/` + `plugins/`; Claude installer under `plugins/`).
- **`_base/SETUP_INSTRUCTIONS.md`** — agent-readable numbered setup steps for wiring up a fresh project. **Each agent sets up only its own runtime**: Claude Code agents run Phases 0–2 + Phase 3 (Claude) + Phases 5–6; Codex agents run Phases 0–2 + Phase 4 (Codex) + Phases 5–6. Phases 0, 1, 2, 5, 6 are idempotent, so a second agent on the other runtime can re-run the file later to set up its side without re-doing or breaking the first agent's work. Each step has an explicit check; on any failure the agent stops and hands control back to the user. Pointed at like `Follow _base/SETUP_INSTRUCTIONS.md`.

**Downstream impact:** none for existing projects; the new installer is opt-in. Newly-seeded projects benefit immediately — pointing an agent at `_base/SETUP_INSTRUCTIONS.md` is now the canonical setup path (`_base/README.md` § "Quick start" updated to reflect this). The file ownership matrix in both `_base/README.md` and `_base/AGENTS.md` now lists `_base/SETUP_INSTRUCTIONS.md` as upstream-owned.

### Add `spec-workflow` skill

New heavyweight skill that drives a plan → build → review → fix loop for a single engineering item, with four standardized artifacts under `specs/<slug>/` (`spec.md`, `design.md`, `tasks.md`, `review.md`). Reuses the existing `subagent-protocol` dispatch + status vocabulary and the existing `implementer` and `reviewer` subagent/skill definitions — no new agent definitions, no experimental flags. Runtime-agnostic: same playbook and artifacts on Claude Code (Task-tool parallel dispatch) and Codex (sequential `/implementer` invocation per task). Composes with the existing PRD chain — `write-a-prd` / `prd-to-plan` / `prd-to-issues` / `prd-to-todos` remain unchanged; spec-workflow accepts a PRD or rough intent as input. Strong "do NOT use for…" guardrails in the wrapper description keep it from auto-triggering on small tasks.

**Downstream impact:** none. New skill; opt-in by invocation. After merging, run `./_base/scripts/gen-skills-table.sh` to regenerate the skills table in this file's sibling `_base/README.md`. No conflicts expected; new files only.

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
