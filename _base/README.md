# Agents Template — Base

> **This is `_base/README.md`**: the authoritative, shared base documentation for the agents template.
> The repo-level `README.md` extends this file. Downstream projects seeded from this template should keep the entire `_base/` directory exactly as inherited (so it merges cleanly on `git fetch template && git merge`) and write their own root-level `README.md` that links here.

Template repository for portable agent behavior contracts and reusable skills in any development project.

This repo is designed to work with both **Claude Code** and **OpenAI Codex**. Copy it into a project, use it as a submodule, or seed a new project from it and keep it wired up as a `template` git remote so you can pull future improvements in (see [Staying in sync with the template](#staying-in-sync-with-the-template)).

**Canonical URL:** `git@github.com:toderian/project_template.git`

## What is in the repo

```text
.
├── AGENTS.md                              # Downstream-owned entrypoint; loads _base/AGENTS.md
├── README.md                              # Downstream-owned README; links to _base/README.md
├── LICENSE
│
├── _base/                                 # Upstream-owned base content — never edit downstream
│   ├── AGENTS.md                          # Base operating contract
│   ├── README.md                          # Base documentation (this file)
│   ├── CHANGELOG.md                       # Base-template changelog
│   ├── SETUP_INSTRUCTIONS.md              # Numbered setup steps for an agent (or human) to execute
│   ├── PROJECT.md.template                # Optional alignment-doc scaffold; copy to ./PROJECT.md to enable /align
│   ├── repos.project.example.md           # Optional downstream repo-registry scaffold; copy to ./.config/repos.project.md
│   ├── repos.map.example                  # Optional local checkout-map example; copy to ./.local/repos.map
│   ├── project.env.example                # Reference env vars; copy to ./project.env at repo root
│   ├── docs/                              # Seed docs layout: tasks, areas, resources, runbooks, archive
│   ├── workbooks/                         # Seed root workbook index
│   ├── plugins/                           # Template-owned Codex plugins and plugin installers
│   │   ├── <plugin-name>/.codex-plugin/plugin.json
│   │   ├── install-codex-plugins.sh
│   │   ├── install-claude-plugins.sh
│   │   └── bootstrap-third-party.sh
│   └── scripts/                           # Template-owned setup, task-system, and validation scripts
│       ├── setup-agents.sh                # One-command Claude + Codex skill/plugin refresh
│       ├── link-skills.sh                 # Links Claude Code skills into ~/.claude/skills
│       ├── seed-docs.sh                   # Seeds docs/ and workbooks/ without overwriting
│       ├── reserve-work-item.sh           # Atomically reserves task/inbox filenames
│       ├── sync-todo-ledgers.sh           # Regenerates task ledgers and generated area blocks
│       ├── check-template-update.sh       # One-command read-only verification after template pulls
│       ├── check-repos-config.sh          # Validates optional .config/repos.project.md and .local/repos.map
│       ├── gen-skills-table.sh            # Regenerates the skills table in _base/README.md
│       ├── check-skills-sync.sh           # Validates skill/wrapper/table consistency
│       └── check-codex-plugins.sh         # Validates bundled Codex plugin manifests/assets
│
│
├── playbooks/                             # Shared workflow logic (single source of truth)
│   ├── skills/                            # Skill playbooks
│   │   ├── productivity/<skill-name>.md
│   │   ├── engineering/<skill-name>.md
│   │   └── misc/<skill-name>.md
│   ├── personalities/                     # Role cards for multi-pass workflows
│   │   ├── manager.md, builder.md, tester.md
│   │   ├── critic.md, reviewer.md, researcher.md
│   ├── templates/                         # Durable artifacts for long-running tasks
│   │   ├── AGENT_TASKS.template.json
│   │   ├── AGENT_PROGRESS.template.md
│   │   ├── AGENT_DECISIONS.template.md
│   │   ├── runbook.template.md
│   │   └── runbook.local.template.md
│   └── meta/                              # Template maintenance
│       ├── UPDATE_PLAN.md
│       └── RESEARCH_SNAPSHOT.md
│
├── skills/                                # Codex skill wrappers (thin)
│   ├── <bucket>/<skill-name>/SKILL.md
│   └── install-codex-skills.sh
└── .claude/
    ├── skills/                            # Claude Code skill wrappers (thin)
    │   └── <bucket>/<skill-name>/SKILL.md
    ├── agents/                            # Claude Code subagent definitions
    │   ├── implementer.md, reviewer.md, plan-critic.md
    │   ├── spec-validator.md, security-auditor.md
    │   └── researcher.md
    ├── hooks/                             # PreToolUse hook scripts
    └── settings.json                      # Hook configuration
```

## Core design

The template encodes a few strong defaults:

1. Start from first principles.
2. Inspect the real repo before acting.
3. Make the smallest useful change.
4. Test it.
5. Critique it.
6. Review it.
7. Repeat until the result is strong enough to ship.

## Task System Quickstart

The task system's golden path is:

```text
/init -> /capture-idea -> /triage-inbox discovery gate -> promote/drop/defer/append
      -> /roadmap -> pre-implementation gate -> implement/execute
      -> /complete-task
      -> _base/scripts/sync-todo-ledgers.sh --check

# Periodic health check:
/audit-todos          # report-only audit of active tasks against code/tests/docs
```

Task files own status and detail, the roadmap owns placement, and ledgers/area pages are generated.
The primary knowledge base lives in `docs/resources/CONTEXT.md`, `docs/resources/<area>/summary.md`,
`docs/resources/<area>/dependency-graph.md`, `docs/resources/<area>/contracts/<feature-slug>.md`,
`docs/resources/<area>/runbooks/<scenario-slug>.md`, and
`docs/resources/<area>/components/<component-slug>/CONTEXT.md`; root `CONTEXT.md` is a pointer/fallback.
Projects that span multiple repos can opt into a committed `.config/repos.project.md` registry, created from
`_base/repos.project.example.md`, plus a gitignored `.local/repos.map` checkout map, created from
`_base/repos.map.example`. Repo slugs from `.config/repos.project.md` are the stable names for task `Repos`
metadata and cross-repo source paths such as `<repo-slug>:<repo-relative-path>`; absolute local paths
stay out of committed docs. Set this up during `_base/SETUP_INSTRUCTIONS.md` Phase 2c, before seeding
docs or creating multi-repo tasks/contracts, when the project needs it.
Raw source material waiting for extraction lives in `docs/resources/_inbox/`, and curated digests live
under `docs/resources/_digests/<area-or-bucket>/` so distilled knowledge stays segregated by area
before stable facts are promoted into canonical docs. Rerunnable reports, audits, inventories, and
migration proposals live under `docs/resources/_reports/<workflow>/` with timestamped filenames so
repeat runs preserve previous observations.
Long-lived committed source documents and binaries live under `docs/resources/<area>/attachments/`
with nearby Markdown metadata or an attachment index documenting purpose, provenance, area or owner,
and update guidance.
Repeated operational procedures such as SSH, setup, service inspection, and debugging live as
sanitized runbooks under `docs/resources/<area>/runbooks/`; real placeholder values live in ignored
`.local/runbooks/` binding files.
Reusable workbook bundles live under root `workbooks/`, one folder per workbook, with workbook-local
scripts, data, assets, templates, examples, outputs, support files, and dependencies declared in the
workbook `README.md`.
See [`playbooks/conventions/task-system-quickstart.md`](../playbooks/conventions/task-system-quickstart.md),
[`playbooks/conventions/knowledge-base-quickstart.md`](../playbooks/conventions/knowledge-base-quickstart.md),
[`playbooks/conventions/generated-artifacts.md`](../playbooks/conventions/generated-artifacts.md),
[`playbooks/conventions/runbook-convention.md`](../playbooks/conventions/runbook-convention.md), and
[`playbooks/conventions/workbook-convention.md`](../playbooks/conventions/workbook-convention.md)
for the full command map and source-of-truth split.

Use `/audit-todos` periodically to compare active tasks with current code, tests, docs, roadmap,
ledgers, area pages, and resources. It is report-only by default and delegates any closeout, follow-up
capture, task creation, or roadmap cleanup to `/complete-task`, `/capture-idea`, `/add-task`, or
`/roadmap`.

## Skills and playbooks

Skills are reusable agent capabilities invoked by name. Claude Code exposes repo skills as slash-style
commands such as `/tdd`, `/qa`, and `/grill-me`. Codex loads skills into the model context instead; in
Codex, use natural language ("tidy this repo") or name the skill explicitly (`$tidy-repo`) rather than
typing `/tidy-repo` as a TUI command.

### Architecture

```
skills/<bucket>/<name>/SKILL.md          →  thin Codex wrapper
.claude/skills/<bucket>/<name>/SKILL.md  →  thin Claude Code wrapper
playbooks/skills/<bucket>/<name>.md      →  shared workflow logic (authoritative)
.claude-plugin/plugin.json               →  active-skill manifest (single source of truth)
```

Active skills are listed in `.claude-plugin/plugin.json` — the manifest is what the sync/install scripts iterate over, not the filesystem. Skills are grouped into buckets (`engineering/`, `productivity/`, `misc/`, `personal/`) to keep the catalogue legible as it grows.

Most wrappers point to the same playbook. **The playbook is the single source of truth.** The only
agent-only exceptions are `implementer` and `reviewer`: their canonical behavior is the subagent
protocol plus the matching personality cards. When changing a workflow, update the playbook first; keep
the wrappers thin.

### Available skills

The table below lists the skills authored in this template (base tier). Downstream projects that add their own skills should list those in their own `README.md`, not here. Vendored Codex plugins ship additional skills not listed here — `_base/plugins/superpowers/` (~14 skills: brainstorming, dispatching-parallel-agents, writing-plans, executing-plans, test-driven-development, systematic-debugging, etc.) and `_base/plugins/github/` (PR/issue/CI workflows). Those become available when you run `./_base/plugins/install-codex-plugins.sh` (Codex) or load the equivalent plugin in Claude Code.

<!-- BEGIN skills-table -->
<!-- This block is auto-generated by _base/scripts/gen-skills-table.sh from .claude-plugin/plugin.json — do not edit by hand. -->

| Skill | Bucket | Description |
|-------|--------|-------------|
| add-task | productivity | Create a full area-prefixed task in docs/tasks_manager/_todos/ with phases, acceptance criteria, related tests, priority, and optional roadmap placement. Use when the user says "add task", "create task", "file a task", "track this task", or gives clear actionable work that should skip inbox capture. |
| align | productivity | Check a proposed feature or change against the project's PROJECT.md (vision, goals, scope, constraints) and report ALIGNED, NEEDS_CLARIFICATION, or OUT_OF_SCOPE. Use when starting non-trivial work, when scope feels uncertain, or before planning-workflow. Requires PROJECT.md at the repo root. |
| audit-todos | productivity | Audit active task files against current repo state to find outdated, completed, obsolete, duplicated, or follow-up-ready work. Use when the user says "audit todos", "audit tasks", "review active tasks", or asks for periodic task backlog health checks. |
| capture-idea | productivity | Capture an idea into the inbox (docs/tasks_manager/_inbox/) as an I-NNN file with near-zero friction. Use whenever the user says "capture", "add to inbox", "note this idea", "jot down", or shares a feature/bug/idea they want recorded for later — even if they don't explicitly ask to use a skill. |
| complete-task | productivity | Complete or cancel a task, fill its completion harvest and summary, archive it, then sync and strictly validate task ledgers. Use when the user says "complete task", "finish task", "close task", "cancel task", or asks to archive a done task. |
| cross-repo-feature | engineering | Capture a concrete feature contract under docs/resources/<area>/contracts/<feature-slug>.md, including repo responsibilities, API/schema/event/env/CLI/Docker boundaries, compatibility, rollout order, and verification. Use when the user says "cross-repo feature", "feature contract", or asks to coordinate a change across repos. |
| define-area | engineering | Define or refresh a durable docs/resources/<area>/ context for a domain or product capability, including participant repos, dependency graph, install modes, runtime dependencies, and known docs. Use when the user says "define area", "index area", "map area", or asks to establish cross-repo area knowledge. |
| describe-component | engineering | Generate or refresh a docs-primary component CONTEXT.md describing responsibility, public interface, dependencies, data owned, invariants, and tests. Use when the user wants to "describe a component", "document this module/service", map a subsystem's boundaries, or onboard to/hand off a part of the codebase. Distinct from docs/resources/CONTEXT.md domain glossary work (that's grill-with-docs). |
| design-an-interface | misc | Generate multiple radically different interface designs for a module using parallel sub-agents when available. Use when user wants to design an API, explore interface options, compare module shapes, or mentions "design it twice". |
| diagnose | engineering | Disciplined diagnosis loop for hard bugs and performance regressions. Reproduce → minimise → hypothesise → instrument → fix → regression-test. Use when user says "diagnose this" / "debug this", reports a bug, says something is broken/throwing/failing, or describes a performance regression. |
| distill-knowledge | engineering | Distill raw documents, notes, exports, or pasted context into Markdown digests and durable docs/resources knowledge-base updates. Use when the user says "distill knowledge", "process raw docs", "summarize these docs", "ingest docs", or points to docs/resources/_inbox/ material. |
| edit-article | personal | Edit and improve articles by restructuring sections, improving clarity, and tightening prose. Use when user wants to edit, revise, or improve an article draft. |
| execute-plan | engineering | Execute an approved task or implementation plan phase-by-phase, committing each completed phase and running repeated independent reviews. Use when the user says "execute plan", "execute-plan", or "/execute-plan", or points to docs/tasks_manager/_todos/<TASK>.md or docs/_plans/<slug>.md and wants it implemented. |
| frontend-design | misc | Create distinctive, production-grade frontend interfaces with high design quality. Use when the user asks to build web components, pages, or applications. Generates creative, polished code that avoids generic AI aesthetics. |
| git-guardrails-claude-code | misc | Set up Claude Code hooks to block dangerous git commands (push, reset --hard, clean, branch -D, etc.) before they execute. Use when user wants to prevent destructive git operations, add git safety hooks, or block git push/reset in Claude Code. |
| github-triage | misc | Triage GitHub issues through a label-based state machine with interactive grilling sessions. Use when user wants to triage issues, review incoming bugs or feature requests, prepare issues for an AFK agent, or manage issue workflow. |
| grill-me | productivity | Interview the user relentlessly about a plan or design until reaching shared understanding, resolving each branch of the decision tree. Use when user wants to stress-test a plan, get grilled on their design, or mentions "grill me". |
| grill-with-docs | engineering | Grilling session that challenges a plan against the existing domain model, sharpens terminology, and updates docs/resources/CONTEXT.md plus ADRs inline as decisions crystallise. Use when the user wants to stress-test a plan against the project's language and documented decisions, when a CONTEXT.md or ADR log exists, or when starting one. |
| handoff | productivity | Compact the current conversation into a handoff document so a fresh agent can pick up the work. Use when the user wants a session summary written to disk for later continuation, mentions "handing off", or is wrapping up a long session. |
| implementer | misc | Act as an implementer for a single task slice. Use when implementing focused work from a plan, following the subagent protocol with scope fencing and structured reporting. |
| improve-codebase-architecture | engineering | Explore a codebase to find opportunities for architectural improvement, focusing on making the codebase more testable by deepening shallow modules. Use when user wants to improve architecture, find refactoring opportunities, consolidate tightly-coupled modules, or make a codebase more AI-navigable. |
| init | misc | Initialize project idea/task tracking structure. Use when user wants to set up docs/ with inbox, tasks, areas, durable plans, resources, archive, roadmap, and generated ledgers. |
| migrate-to-shoehorn | engineering | Migrate test files from `as` type assertions to @total-typescript/shoehorn. Use when user mentions shoehorn, wants to replace `as` in tests, or needs partial test data. |
| migration-safety | engineering | Generate safe, reversible database schema migrations and review proposed ones for production hazards (table-rewrite locks, NOT-NULL-without-backfill, missing CONCURRENTLY, irreversible DROPs). Default focus PostgreSQL with Liquibase or Flyway; safety rules generalize to MySQL and SQLite. Use when the user mentions migration, schema change, alter table, add/drop column, add index, backfill, Liquibase, Flyway, or zero-downtime DDL. |
| obsidian-vault | personal | Search, create, and manage notes in the Obsidian vault with wikilinks and index notes. Use when user wants to find, create, or organize notes in Obsidian. |
| planning-workflow | productivity | Seven-step pre-implementation planning workflow. Use when the user wants to plan a non-trivial change before writing code — multi-file features, multiple plausible approaches, or work that needs scope bounded. Pairs with the plan-critic subagent for adversarial review against the five-axis rubric. |
| prd-to-issues | productivity | Break a PRD into independently-grabbable GitHub issues using tracer-bullet vertical slices. Use when user wants to convert a PRD to issues, create implementation tickets, or break down a PRD into work items. |
| prd-to-plan | productivity | Turn a PRD into a multi-phase implementation plan using tracer-bullet vertical slices, saved as docs/_plans/<slug>.md. Use when user wants to break down a PRD, create an implementation plan, plan phases from a PRD, or mentions "tracer bullets". |
| prd-to-todos | productivity | Extract actionable tasks from a PRD and create area-prefixed task files. Use when user wants to convert a PRD into trackable tasks in docs/tasks_manager/_todos/. |
| prototype | engineering | Build a throwaway prototype to flesh out a design before committing to it. Routes between two branches — a runnable terminal app for state/business-logic questions, or several radically different UI variations toggleable from one route. Use when the user wants to prototype, sanity-check a data model or state machine, mock up a UI, explore design options, or says "prototype this", "let me play with it", "try a few designs". |
| qa | productivity | Interactive QA session where user reports bugs or issues conversationally, and the agent files GitHub issues. Explores the codebase in the background for context and domain language. Use when user wants to report bugs, do QA, file issues conversationally, or mentions "QA session". |
| refresh-context | engineering | Refresh the docs-primary knowledge base and detect stale architecture or domain context. Use when the user asks to "refresh context", "reindex context", "update knowledge base", or "check context drift". |
| request-refactor-plan | engineering | Create a detailed refactor plan with tiny commits via user interview, then file it as a GitHub issue. Use when user wants to plan a refactor, create a refactoring RFC, or break a refactor into safe incremental steps. |
| reviewer | misc | Two-stage review of implementation work. Use when reviewing completed task output for spec compliance and code quality. |
| roadmap | productivity | Maintain docs/tasks_manager/_roadmap.md — the placement-only Urgent/Now/Next/Later/Someday ordering for tasks and inbox ideas. Use when the user wants to "plan the roadmap", "what's next", reprioritize/sequence work, schedule tasks, or refresh the roadmap. Distinct from per-change planning (planning-workflow / prd-to-plan). |
| scaffold-exercises | misc | Create exercise directory structures with sections, problems, solutions, and explainers that pass linting. Use when user wants to scaffold exercises, create exercise stubs, or set up a new course section. |
| security-review-owasp | engineering | Apply current OWASP standards (Top 10:2025, ASVS 5.0, LLM Top 10 2025, Agentic AI 2026) when writing or reviewing code. Use when reviewing code for security issues, implementing auth/authz, handling user input, designing API endpoints, building AI agent systems, integrating LLMs/RAG, or discussing application security. |
| setup-pre-commit | engineering | Set up Husky pre-commit hooks with lint-staged (Prettier), type checking, and tests in the current repo. Use when user wants to add pre-commit hooks, set up Husky, configure lint-staged, or add commit-time formatting/typechecking/testing. |
| spec-workflow | engineering | Heavyweight spec-driven development loop (plan → build → review → fix) for a single engineering item, with four artifacts under specs/<slug>/ (spec.md, design.md, tasks.md, review.md) and parallel implementer dispatch via the subagent-protocol. Use when the user asks to "spec it out", run a spec-driven workflow, plan + build + review a non-trivial feature, parallelize implementer subagents against a written design, or mentions "spec workflow" / "spec-driven". Do NOT use for one-file edits, typos, trivial bug fixes, exploratory spikes, or anything the default single-agent operating loop can handle in one pass — this skill is intentionally heavy. |
| subagent-protocol | productivity | Multi-agent coordination protocol with status vocabulary, dispatch format, and two-stage review. Use when dispatching subagents, coordinating multi-agent work, or reviewing implementation output. |
| tdd | engineering | Test-driven development with red-green-refactor loop. Use when user wants to build features or fix bugs using TDD, mentions "red-green-refactor", wants integration tests, or asks for test-first development. |
| tidy-repo | productivity | Inventory a messy repo's scattered TODOs, loose docs, and orphan files, then propose a non-destructive migration into the docs/tasks_manager + docs/resources structure. Use when the user says "tidy this repo", "systematize", "clean up the mess", "organize my tasks/docs", or describes an inherited repo with scattered TODOs, stray docs, and unrelated files. |
| triage-inbox | productivity | Review captured inbox ideas (docs/tasks_manager/_inbox/) and promote worthwhile ones into full area-prefixed tasks, or drop them. Use when the user says "triage inbox", "review the inbox", "process my ideas", "clear the inbox", or wants to turn captured ideas into actionable tasks. |
| triage-issue | misc | Triage a bug or issue through a two-role state machine (category + state) and produce a `ready-for-agent` GitHub issue with a TDD-based fix plan, by exploring the codebase to find the root cause. Use when the user wants to "triage" a bug, investigate an issue, file an issue, plan a fix, or move an issue toward `ready-for-agent`. |
| ubiquitous-language | engineering | Extract a DDD-style ubiquitous language glossary from the current conversation, flagging ambiguities and proposing canonical terms. Saves to UBIQUITOUS_LANGUAGE.md. Use when user wants to define domain terms, build a glossary, harden terminology, create a ubiquitous language, or mentions "domain model" or "DDD". |
| write-a-prd | productivity | Create a PRD through user interview, codebase exploration, and module design, then submit as a GitHub issue. Use when user wants to write a PRD, create a product requirements document, or plan a new feature. |
| write-a-skill | productivity | Create new agent skills with proper structure, progressive disclosure, and bundled resources. Use when user wants to create, write, or build a new skill. |
| zoom-out | engineering | Step up a layer of abstraction and produce a map of the relevant modules and callers, using the project's domain glossary. Use when starting work in an unfamiliar area of the codebase, when broader context is needed, or when a narrow trace has lost the bigger picture. |

<!-- END skills-table -->

### Adding a new skill

1. Pick a bucket (`engineering`, `productivity`, `misc`, `personal`).
2. Create the playbook: `playbooks/skills/<bucket>/<name>.md`
3. Create the Codex wrapper: `skills/<bucket>/<name>/SKILL.md`
4. Create the Claude wrapper: `.claude/skills/<bucket>/<name>/SKILL.md`
5. Add `./skills/<bucket>/<name>` to the `skills` array in `.claude-plugin/plugin.json` (keep it alphabetically sorted within the bucket).
6. Regenerate the skills table: `./_base/scripts/gen-skills-table.sh`
7. Validate consistency: `./_base/scripts/check-skills-sync.sh` (fix any findings and re-run until clean)
8. For Codex, run `skills/install-codex-skills.sh` and restart Codex

See `playbooks/skills/productivity/write-a-skill.md` for the full skill authoring guide.

### Validating skill/wrapper consistency

`_base/scripts/check-skills-sync.sh` verifies that every playbook has matching Codex + Claude wrappers, that frontmatter names/descriptions stay in sync, that the auto-generated skills table is up-to-date, and that personalities aren't accidentally exposed as slash commands. It calls `gen-skills-table.sh --check`, so validation is read-only. Designed to be called by an agent in a loop:

```bash
./_base/scripts/check-skills-sync.sh
# Read each finding (line format: SEVERITY  CHECK_ID  PATH  [details]).
# Fix one or a batch, then re-run. Stop when output is "OK ...".
```

Severities: **BLOCKER** (missing/orphan files, broken references), **DRIFT** (out-of-sync metadata, mechanically fixable), **STYLE** (advisory thin-wrapper / convention violations). The script exits non-zero on BLOCKER or DRIFT; STYLE alone is allowed.

`_base/scripts/check-codex-plugins.sh` validates bundled Codex plugin manifests, referenced skill/app paths, plugin skill `SKILL.md` files, app JSON, optional MCP JSON, and declared interface assets. `_base/plugins/install-codex-plugins.sh` runs it before changing local symlinks or marketplace entries.

Template-owned scripts live under `_base/scripts/`, and template-owned bundled plugins live under `_base/plugins/`, so the root `scripts/` and `plugins/` directories remain available for downstream project tooling. Some helpers validate upstream-owned content, while task-system and setup helpers intentionally operate on the downstream repo state from their upstream-owned location. Downstream projects should not re-implement them; pull updates from the template and re-run.

`_base/scripts/check-template-update.sh` is the standard read-only, agent-runtime-independent
post-merge verifier for downstream repos. It prints the current `BASE_VERSION`, syntax-checks template
shell scripts, runs the template validation checks, exits non-zero when anything needs attention, and
is designed for an agent to run, fix reported failures, and rerun until green.

`_base/scripts/check-repos-config.sh` validates an optional downstream `.config/repos.project.md` registry and any
task `Repos` metadata. Default mode is safe for projects that have not opted in. Use
`_base/scripts/check-repos-config.sh --local` after configuring `.local/repos.map` to verify required
repo mappings, absolute paths, and checkout directories.

## Platform support

| Feature | Claude Code | Codex |
|---------|------------|-------|
| AGENTS.md (+ _base/AGENTS.md) | Auto-loaded; loads `_base/AGENTS.md` by instruction | Auto-loaded; loads `_base/AGENTS.md` by instruction |
| Skills | `.claude/skills/` auto-discovered as slash-style commands | `skills/` via `install-codex-skills.sh`; invoke by natural language or `$skill-name`, not TUI slash commands |
| Plugins | `_base/plugins/install-claude-plugins.sh` can enable curated Claude Code plugins in `~/.claude/settings.json` | `_base/plugins/` via `install-codex-plugins.sh` and local marketplace entries |
| Agent definitions | `.claude/agents/` native subagent dispatch (`implementer`, `reviewer`, `plan-critic`, `spec-validator`, `security-auditor`, `researcher`) | Use Codex multi-agent tools when available; otherwise `skills/misc/implementer` and `skills/misc/reviewer` install as flat behavioral skills, and other roles run on the main thread under their cited personality + skill/convention |
| Hooks | `.claude/settings.json` PreToolUse | Codex approval policy (`suggest`/`auto-edit`/`full-auto`) |
| Per-directory overrides | Nested `AGENTS.md` in subdirectories | Not supported — root `AGENTS.md` only |

All workflow logic lives in `playbooks/` (shared). Platform-specific features in `.claude/`, `skills/`, and `_base/plugins/` are additive — a Codex user reading only `AGENTS.md` + `_base/AGENTS.md` + `playbooks/` + `skills/` + `_base/plugins/` gets the full picture.

## Using with Claude Code

Claude Code discovers skills automatically from `.claude/skills/`. No installation needed — open the project and skills are available as slash commands.
For global skill symlinks and curated plugin entries, run the shared setup command:

```bash
./_base/scripts/setup-agents.sh
# Then restart Claude Code
```

Claude-specific skill metadata:

```yaml
---
name: skill-name
description: What it does. Use when [triggers].
disable-model-invocation: true   # hand off to playbook, don't generate
---
```

## Using with Codex

Codex skills and plugins are installed by the shared setup command:

```bash
./_base/scripts/setup-agents.sh
# Then restart Codex
```

Codex skills are not TUI slash commands. After restart, say what you want in plain language, for
example `tidy this repo`, or name the skill explicitly as `$tidy-repo`.

For manual/debugging use, Codex skills live in `skills/` and are symlinked into `~/.codex/skills/` by
`./skills/install-codex-skills.sh`. Codex plugins live in `_base/plugins/` and use the `.codex-plugin/plugin.json`
manifest layout:

```bash
./skills/install-codex-skills.sh
./_base/plugins/install-codex-plugins.sh
```

The plugin installer symlinks repo plugins into `~/plugins/` by default and
adds local marketplace entries pointing at `./_base/plugins/<name>` to
`~/.agents/plugins/marketplace.json`. It first
runs `_base/scripts/check-codex-plugins.sh` so malformed manifests or missing
plugin assets fail before any local install state changes.

Codex skill metadata:

```yaml
---
name: skill-name
description: What it does. Use when [triggers].
---
```

## Third-party plugins (own installers)

Some upstream tools ship multi-platform installers and don't fit the `playbooks/` + dual-wrapper convention. They're not vendored — `_base/plugins/bootstrap-third-party.sh` runs (or documents) their native install paths instead.

| Tool | What it adds | Install path |
|------|--------------|--------------|
| `get-shit-done-cc` | Spec-driven dev workflow (researchers/planners/executors) | `npx get-shit-done-cc --claude --global` and `--codex --global` |
| `context-mode` | MCP server + hooks that sandbox tool output (~98% context savings on Claude, ~60% on Codex) | `/plugin marketplace add mksglu/context-mode` |
| `claude-mem` | Cross-session memory via MCP; ships both `.claude-plugin/` and `.codex-plugin/` | `/plugin marketplace add thedotmack/claude-mem` |

Run `./_base/plugins/bootstrap-third-party.sh` to install the npm-based ones and print the marketplace commands for the others. Toggle each section with env vars (`INSTALL_GSD`, `INSTALL_CONTEXT_MODE`, `INSTALL_CLAUDE_MEM`).

## Quick start

**Primary path — point an agent at `_base/SETUP_INSTRUCTIONS.md`.**
That file contains numbered, mechanical setup steps with per-step checks; an agent reading it executes the whole thing autonomously and stops on any failed check. Use it like:

```
Follow _base/SETUP_INSTRUCTIONS.md.
```

The options below describe how to *seed* a project (i.e. how the files get onto disk in the first place); `SETUP_INSTRUCTIONS.md` then walks the agent through everything after that (template remote, runtime installers, project-specific overrides, verification).

### Option 1: copy into a repo

Copy these into the target project (then point an agent at `_base/SETUP_INSTRUCTIONS.md`, or run the installers yourself):

| Artifact | Required for | Notes |
|----------|--------------|-------|
| `AGENTS.md` | Both | Auto-loaded entrypoint; downstream-owned (project-specific overrides go here) |
| `_base/` | Both | Base operating contract, base README, base changelog, **base setup instructions**; upstream-owned (do not edit downstream) |
| `_base/docs/` | Both (optional) | Seed layout for `docs/tasks_manager/`, `docs/areas/`, docs-primary knowledge resources, raw knowledge inbox/digests/reports, and `docs/archive/`; copy via `/init` |
| `_base/workbooks/` | Both (optional) | Seed root `workbooks/README.md` as the workbook index; copy via `/init` |
| `playbooks/` | Both | Authoritative workflow logic, role cards, templates |
| `.claude/` | Claude Code | Skills, native subagents, hook scripts, settings |
| `skills/` | Codex | Thin wrappers + `install-codex-skills.sh` |
| `_base/scripts/setup-agents.sh` | Both | One-command skill/plugin validation and install/refresh for Claude Code and Codex |
| `_base/plugins/` | Both | Vendored plugins, `install-codex-plugins.sh`, `install-claude-plugins.sh`, `bootstrap-third-party.sh` |
| `_base/project.env.example` | Both (optional) | Copy to `project.env` at the repo root (`cp _base/project.env.example project.env`) to override default install paths |
| `_base/PROJECT.md.template` | Both (optional) | Copy to `PROJECT.md` at the repo root (`cp _base/PROJECT.md.template PROJECT.md`) and fill in to enable the `/align` skill for feature-level alignment gating |
| `_base/repos.project.example.md` | Both (optional) | Copy to `.config/repos.project.md` and edit when the downstream project needs a committed repo registry |
| `_base/repos.map.example` | Both (optional, local-only) | Copy to `.local/repos.map` and edit with machine-local absolute checkout directory paths; `.local/` is gitignored |

After copying or pulling template updates, run the one-command setup:

```bash
./_base/scripts/setup-agents.sh
```

It validates the skill catalog, installs or refreshes Codex skills and plugins, links Claude Code skills
globally, and installs or refreshes Claude Code plugins. The command is idempotent; run it again after
each template update. Restart Codex and Claude Code afterwards so they reload skills and plugins. The
lower-level installers remain available for advanced/manual use. To set up only one runtime, use
`./_base/scripts/setup-agents.sh --codex-only` or `./_base/scripts/setup-agents.sh --claude-only`.

### Option 2: use as a submodule

```bash
git submodule add <this-repo-url> agent-template
```

Then reference the files from the root project or symlink the chosen artifacts into place.

### Option 3: seed a new project from this template

Use this when you want a new project that starts as a full copy of the template but keeps a pointer back to the base so you can pull updates later.

```bash
# 1. Create the new project as a clone of the template
git clone git@github.com:toderian/project_template.git my-new-project
cd my-new-project

# 2. Rewire remotes: origin → your new repo, template → the base template
git remote rename origin template
git remote set-url --push template DISABLE      # prevent accidental pushes to the template
git remote add origin git@github.com:<you>/<my-new-project>.git

# 3. Replace the template's README.md with your project's own README;
#    keep the entire _base/ directory as-is so it can be cleanly updated from upstream.
#    Your README.md should describe your project and link to _base/README.md.
$EDITOR README.md

git add README.md
git commit -m "chore: seed project README from agents template"
git push -u origin HEAD
```

After this, `git remote -v` should show two remotes:

- `origin` — your new project repo (read/write)
- `template` — this repo (`git@github.com:toderian/project_template.git`), fetch-only

A minimal downstream `README.md`:

```markdown
# MyApp

What MyApp does, how to run it, etc.

## Agent contract

This project extends the agents template — see [`_base/README.md`](./_base/README.md)
([upstream](https://github.com/toderian/project_template)).
```

See [Staying in sync with the template](#staying-in-sync-with-the-template) for how to pull updates in.

## Staying in sync with the template

Every project seeded from this template should keep `git@github.com:toderian/project_template.git` configured as a `template` git remote. This is how downstream projects receive future improvements (new skills, playbook fixes, hook updates) without having to re-copy by hand.

### One-time setup in an existing project

If a downstream project was started by copying files (not cloning), add the remote retroactively:

```bash
git remote add template git@github.com:toderian/project_template.git
git remote set-url --push template DISABLE
git fetch template
```

### Pulling updates from the template

```bash
git fetch template
git log --oneline HEAD..template/master    # preview what's new upstream
git diff HEAD..template/master -- _base/CHANGELOG.md   # human-readable summary + per-change downstream impact
git merge template/master                  # or: git cherry-pick <commit>
./_base/scripts/check-template-update.sh   # read-only verification after the merge
```

Always check `_base/CHANGELOG.md` before merging — each entry includes a **Downstream impact** line that flags expected conflicts, new conventions, or behavior changes. Use `merge` when you want everything; use `cherry-pick` when you only want specific commits (e.g. a new skill but not a hook change you've customized). After the merge, an agent can run `./_base/scripts/check-template-update.sh`, fix any reported failures, and rerun it until it passes.

### File conventions for downstream projects

Each repo file falls into one of three buckets:

**Downstream-owned** (each project writes its own; never conflicts on pulls):

- `README.md` — describes the project, links to `_base/README.md`.
- `AGENTS.md` — entrypoint auto-loaded by agents; instructs them to read `_base/AGENTS.md` and then applies any project-specific overrides.
- `.config/repos.project.md` (optional) — committed repo registry created from `_base/repos.project.example.md` when
  a project needs stable repo slugs, branch/work policy, and task `Repos` metadata.
- `workbooks/` — workbook bundles, one folder per workbook. Seeded from `_base/workbooks/README.md`,
  then owned by the downstream project.

**Upstream-owned** — everything under `_base/`. Do not edit; flows in cleanly from `git fetch template && git merge`. Simple rule for merge conflicts: always accept upstream for `_base/*`.

- `_base/README.md` — base documentation.
- `_base/AGENTS.md` — base operating contract.
- `_base/CHANGELOG.md` — base-template changelog; read this after `git fetch template` to know what's coming in. Downstream projects may keep their own root-level `CHANGELOG.md` for project-specific changes (downstream-owned, never collides).
- `_base/SETUP_INSTRUCTIONS.md` — agent-readable numbered setup steps. Point an agent at this file to wire up a fresh project end-to-end (template remote, runtime installers, downstream-slot replacements, verification).
- `_base/PROJECT.md.template` — alignment-doc scaffold; copy to `PROJECT.md` at the repo root if you want feature-level alignment gating via `/align`.
- `_base/repos.project.example.md` — optional scaffold for downstream `.config/repos.project.md`.
- `_base/repos.map.example` — optional example for local `.local/repos.map` checkout mappings.
- `_base/docs/` — seed docs layout for the task manager, generated area views, docs-primary
  knowledge resources, raw knowledge inbox/digests/reports, runbooks, and archive.
- `_base/workbooks/` — seed root workbook index. Pull updates from upstream; downstream workbook
  contents live in root `workbooks/`.

**Mixed** (manual merge required):

- `.claude/settings.json` — merge hook entries by hand; don't blindly accept upstream.
- `playbooks/skills/*` and `skills/*` / `.claude/skills/*` — accept upstream for skills you haven't customized; keep downstream for skills you've forked.
- `project.env` — never committed; not a conflict source.
- `.local/repos.map` — never committed; machine-local checkout paths for repo slugs in `.config/repos.project.md`.
- `.local/runbooks/` — never committed; machine-local placeholder bindings for sanitized runbooks.
- `PROJECT.md` — downstream-owned alignment doc, if seeded from `_base/PROJECT.md.template`. The template flows in cleanly; the seeded `PROJECT.md` is the project's own and is not touched by template pulls.

### Agent instructions for downstream projects

When operating in a project that was seeded from this template, agents should:

1. On request to "update from the template" or "pull template updates", run `git fetch template` and show the user the diff before merging.
2. Never push to the `template` remote. The push URL is disabled by convention; if it is not, treat any push there as out of scope.
3. If the `template` remote is missing in a project that clearly originated from this template (presence of `AGENTS.md` + `_base/`, `playbooks/`, `.claude/skills/`), offer to add it with the one-time setup commands above.
4. Never edit anything under `_base/` in a downstream project. Suggested base-contract changes belong upstream in the template repo itself.

## Recommended adoption pattern

### Minimum adoption

- place `AGENTS.md` at the project root and copy the `_base/` directory alongside it
- copy the skills and plugins you need

### Stronger adoption

- use `manager.md`, `builder.md`, `tester.md`, `critic.md`, and `reviewer.md` as explicit passes or sub-agent roles
- copy the files in `playbooks/templates/` for durable progress, task, and decision state
- require agents to use conventional commit summaries plus a commit body
- define branch mode up front: default branch for downstream template-maintenance repos, explicit task
  branches for working/product repos, or `.config/repos.project.md` work modes for multi-repo projects
- rerun `playbooks/meta/UPDATE_PLAN.md` whenever you change the project's agent doctrine

## Examples

### Example 1: single-agent task

```text
Read AGENTS.md (and _base/AGENTS.md, which it loads) and solve this task as one agent.
Work sequentially as manager, builder, tester, critic, and reviewer.
Do not stop at the first plausible answer.
Keep the final output concise and evidence-based.
```

### Example 2: multi-role task

```text
Manager: frame the task, define done, and split the work.
Builder: implement the smallest useful change.
Tester: verify behavior and regressions.
Critic: challenge assumptions and propose a better version.
Reviewer: decide whether the result is ready to merge.
If the critic or tester finds a real problem, loop again.
```

### Example 3: commit and push behavior

```text
In downstream template-maintenance repos, work directly on main/master.
In working/product repos, use the explicit task branch named at task start.
Commit each coherent, reviewable slice with a conventional summary line and a body explaining what changed and why.
Never commit unrelated dirty files.
Do not push unless I ask.
```

### Example 4: updating the template itself

```text
Use researcher.md.
Rerun playbooks/meta/UPDATE_PLAN.md.
Check the latest primary sources.
Update playbooks/meta/RESEARCH_SNAPSHOT.md, _base/AGENTS.md, and _base/README.md examples together.
```

### Example 5: spec-driven development with `/spec-workflow`

Use the [`spec-workflow`](../playbooks/skills/engineering/spec-workflow.md) skill when work is large enough to warrant an up-front spec, parallel implementer dispatch, and an explicit reviewer pass. **Not** for one-file edits, typos, or exploratory spikes — the default operating loop handles those.

Invoke it like this:

```text
Use /spec-workflow.
Input: <PRD link, issue #, plan file, or rough intent>.
Drive the plan → build → review → fix loop end-to-end.
Stop when the reviewer passes, or escalate to me after 3 iterations.
```

The skill creates `specs/<slug>/` at the project root and populates it with four artifacts (`spec.md`, `design.md`, `tasks.md`, `review.md`). Phase 2 dispatches implementer subagents per task (parallel on Claude Code via the `Task` tool; sequential on Codex via `/implementer`); Phase 3 runs a single reviewer pass (two-stage: spec compliance + code quality) and appends to `review.md`. On a failed review, fix tasks are appended to `tasks.md` and the loop runs again. Full mechanics in [`playbooks/skills/engineering/spec-workflow.md`](../playbooks/skills/engineering/spec-workflow.md).

## Update workflow

1. Run `playbooks/meta/UPDATE_PLAN.md`.
2. Refresh `playbooks/meta/RESEARCH_SNAPSHOT.md`.
3. Update `_base/AGENTS.md` and `playbooks/personalities/` only where evidence supports a change.
4. Review the repo for clarity and portability.
5. Update `_base/README.md` examples so adoption stays easy.
