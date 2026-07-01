# Agents Template — Base

> **This is `_base/README.md`**: the authoritative, shared base documentation for the agents template.
> The repo-level `README.md` extends this file. Downstream projects seeded from this template should keep the entire `_base/` directory exactly as inherited (so it merges cleanly on `git fetch template && git merge`) and write their own root-level `README.md` that links here.

Template repository for portable agent behavior contracts and reusable skills in any development project.

This repo is designed to work primarily with **Claude Code** and **OpenAI Codex**. It also includes an experimental, removable **Antigravity** (`agy`) adapter that consumes the same shared playbooks through generated wrappers. Copy it into a project, use it as a submodule, or seed a new project from it and keep it wired up as a `template` git remote so you can pull future improvements in (see [Staying in sync with the template](#staying-in-sync-with-the-template)).

**Canonical URL:** `git@github.com:toderian/project_template.git`

## What is in the repo

```text
.
├── AGENTS.md                              # Downstream-owned entrypoint; loads _base/AGENTS.md
├── README.md                              # Downstream-owned README; links to _base/README.md
├── .gitattributes                         # Downstream-owned file with template merge-rule block
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
│       ├── setup-agents.sh                # One-command Claude + Codex refresh; optional Antigravity wrapper generation
│       ├── setup-template-merge-rules.sh  # Configures template/downstream merge drivers
│       ├── link-skills.sh                 # Links Claude Code skills into ~/.claude/skills
│       ├── seed-docs.sh                   # Seeds docs/ and workbooks/ without overwriting
│       ├── reserve-work-item.sh           # Atomically reserves task/inbox filenames
│       ├── sync-todo-ledgers.sh           # Regenerates task ledgers and generated area blocks
│       ├── check-template-update.sh       # One-command read-only verification after template pulls
│       ├── check-repos-config.sh          # Validates optional .config/repos.project.md and .local/repos.map
│       ├── gen-skills-table.sh            # Regenerates the skills table in _base/README.md
│       ├── check-skills-sync.sh           # Validates skill/wrapper/table consistency
│       ├── gen-antigravity-skills.sh      # Generates experimental .agents/skills wrappers
│       ├── check-antigravity-skills.sh    # Validates generated Antigravity wrappers
│       ├── check-codex-plugins.sh         # Validates bundled Codex plugin manifests/assets
│       └── check-codex-agents.sh          # Validates committed .codex/agents mirrors and ignore rules
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
│   │   ├── resource-inbox-batch.template.md
│   │   ├── area-sources.template.md
│   │   ├── runbook.template.md
│   │   └── runbook.local.template.md
│   └── meta/                              # Template maintenance
│       ├── UPDATE_PLAN.md
│       └── RESEARCH_SNAPSHOT.md
│
├── skills/                                # Codex skill wrappers (thin)
│   ├── <bucket>/<skill-name>/SKILL.md
│   └── install-codex-skills.sh
├── .claude/
│   ├── skills/                            # Claude Code skill wrappers (thin)
│   │   └── <bucket>/<skill-name>/SKILL.md
│   ├── agents/                            # Claude Code subagent definitions
│   │   ├── implementer.md, reviewer.md, plan-critic.md
│   │   ├── spec-validator.md, security-auditor.md
│   │   └── researcher.md
│   ├── hooks/                             # PreToolUse hook scripts
│   └── settings.json                      # Hook configuration
├── .codex/
│   └── agents/                            # Thin project-scoped Codex agent mirrors
└── .agents/
    ├── skill-library.json                 # Selectable skill library and packs
    ├── skills.enabled.json                # Active skill profile/packs
    └── skills/                            # Generated Antigravity wrappers (experimental)
        └── <bucket>/<skill-name>/SKILL.md
```

## Core design

The template encodes a few strong defaults:

1. Start from first principles.
2. Inspect the real repo before acting.
3. Surface material assumptions and ambiguity.
4. Make the smallest useful, surgical change.
5. Test it.
6. Critique it.
7. Review it.
8. Repeat until the result is strong enough to ship.

Autonomy is deliberately bounded. The default level is **L1 local development**: local edits, checks,
iteration, and local commits inside an approved workflow. Higher levels are opt-in ceilings layered on
top of branch/work rules: L2 may update an approved branch and repair its CI, while L3 may open or
update draft PRs and validate PR status. No level authorizes merge, deploy, release, ready-for-review,
force-push/history rewrite, broad connector writes, or secret exposure. See
[`playbooks/conventions/autonomy-levels.md`](../playbooks/conventions/autonomy-levels.md).

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

Task files own status and detail, the roadmap owns placement plus optional dated milestone headings,
and ledgers/area pages are generated. Individual task `Target date` / `Deadline` rows are optional and
should be used only for explicit task-specific scheduling intent.
The primary knowledge base lives in `docs/resources/CONTEXT.md`, `docs/resources/system-map.md`,
`docs/resources/<area>/summary.md`, `docs/resources/<area>/sources.md`,
`docs/resources/<area>/dependency-graph.md`, `docs/resources/<area>/contracts/<feature-slug>.md`,
`docs/resources/<area>/runbooks/<scenario-slug>.md`, and
`docs/resources/<area>/components/<component-slug>/CONTEXT.md`; root `CONTEXT.md` is a
pointer/fallback. Durable specs use lifecycle statuses (`draft`, `accepted`,
`partially-implemented`, `implemented`, `superseded`) so agents can distinguish planned intent from
current system evidence.
Projects that span multiple repos can opt into a committed `.config/repos.project.md` registry, created from
`_base/repos.project.example.md`, plus a gitignored `.local/repos.map` checkout map, created from
`_base/repos.map.example`. Repo slugs from `.config/repos.project.md` are the stable names for task `Repos`
metadata and cross-repo source paths such as `<repo-slug>:<repo-relative-path>`; absolute local paths
stay out of committed docs. New registries may also add `Autonomy max` (`L0`-`L3`) to cap loop
behavior per repo; old 8-column registries remain valid and default to `L1`. Set this up during
`_base/SETUP_INSTRUCTIONS.md` Phase 2c, before seeding docs or creating multi-repo tasks/contracts,
when the project needs it.
Raw source material waiting for extraction lives in `docs/resources/_inbox/`; related files from one
call, teammate handoff, upload bundle, or research bundle may be grouped in an inbox batch folder with
a `README.md` manifest. Curated digests live under `docs/resources/_digests/<area-or-bucket>/` so
distilled knowledge stays segregated by area before stable facts are promoted into canonical docs.
Area source history lives in `docs/resources/<area>/sources.md` so source provenance, why a source was
added, and links to digests/tasks/docs remain traceable. Rerunnable reports, audits, inventories, and
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
workbook `README.md`. Prompt orchestration workbooks are a supported subtype for long-running or
repeatable agent workflows; they may include committed prompt templates, schemas, eval fixtures, trace
documentation, and helper scripts. The base template seeds a vendor-neutral
`prompt-orchestration-long-task/` workbook for planning the next slice from task and workbook state
without adding LangChain or LangGraph as default dependencies.
Agents should not leave substantial, repeatable, expensive, or human-reusable workflows only as inline
shell or Python snippets in a transcript. Turn those workflows into human-runnable artifacts in the
right lane: workbook bundles for reusable script/support-file sets, runbooks for stable operational
procedures, `tools/python/` for committed Python tooling dependencies managed with `uv`, and
`artifacts/README.md` for large/generated/reproducible artifact discovery. For example, if an agent
trains or evaluates a model, the data-prep, training, evaluation, and cleanup commands should live in
`workbooks/<training-slug>/scripts/*.py` or equivalent entrypoints with a README that documents the
methodology, inputs, outputs, dependencies, and cleanup, while model checkpoints or datasets are
registered in `artifacts/README.md` when they meet the artifact-registry threshold.
See the full command map and source-of-truth split in
[`task-system-quickstart.md`](../playbooks/conventions/task-system-quickstart.md),
[`knowledge-base-quickstart.md`](../playbooks/conventions/knowledge-base-quickstart.md),
[`generated-artifacts.md`](../playbooks/conventions/generated-artifacts.md),
[`runbook-convention.md`](../playbooks/conventions/runbook-convention.md),
[`workbook-convention.md`](../playbooks/conventions/workbook-convention.md),
[`adr-convention.md`](../playbooks/conventions/adr-convention.md),
[`autonomy-levels.md`](../playbooks/conventions/autonomy-levels.md),
[`agent-loop-recipes.md`](../playbooks/conventions/agent-loop-recipes.md),
[`prompt-orchestration.md`](../playbooks/conventions/prompt-orchestration.md), and
[`connectors-and-mcp.md`](../playbooks/conventions/connectors-and-mcp.md).

Use `/audit-todos` periodically to compare active tasks with current code, tests, docs, roadmap,
ledgers, area pages, and resources. It is report-only by default and delegates any closeout, follow-up
capture, task creation, or roadmap cleanup to `/complete-task`, `/capture-idea`, `/add-task`, or
`/roadmap`.

## Python tooling environments

When a downstream project needs repo-level Python tooling dependencies, use `uv` and keep that
environment under `tools/python/` rather than at the repository root. This convention is for helper
tooling used by agents or project scripts; it does not make every seeded project a Python package.

Once Python tooling dependencies exist, commit these files:

- `tools/python/pyproject.toml` — declares the Python tooling dependencies.
- `tools/python/uv.lock` — records the exact resolved dependency state. This file is uv-managed; do
  not hand-edit it.
- `tools/python/.python-version` — pins the interpreter version for the tooling environment.

Never commit the virtual environment itself:

- `.venv/` — ignored root scratch environment.
- `tools/python/.venv/` — ignored uv-managed environment for repo-level Python tooling.

Run uv commands from the environment directory, for example:

```bash
cd tools/python && uv sync
cd tools/python && uv run <command>
```

Use `uv add`, `uv remove`, `uv lock`, `uv sync`, and `uv run`; do not use `pip install` directly for
dependencies that should be represented in committed project state. If a project needs multiple
Python tooling environments, create explicit subfolders such as `tools/python/<name>/` and document
each one in the downstream `AGENTS.md`.

Do not create `tools/python/pyproject.toml`, `tools/python/uv.lock`, or
`tools/python/.python-version` until there are real Python tooling dependencies to represent.

## Skills and playbooks

Skills are reusable agent capabilities invoked by name. Claude Code exposes repo skills as slash-style
commands such as `/tdd`, `/qa`, and `/grill-me`. Codex loads skills into the model context instead; in
Codex, use natural language ("tidy this repo") or name the skill explicitly (`$tidy-repo`) rather than
typing `/tidy-repo` as a TUI command. Antigravity support is experimental: `agy` consumes generated
wrappers under `.agents/skills/`, but those wrappers are not a source of truth.

### Architecture

```
skills/<bucket>/<name>/SKILL.md          →  thin Codex wrapper
.claude/skills/<bucket>/<name>/SKILL.md  →  thin Claude Code wrapper
.agents/skills/<bucket>/<name>/SKILL.md  →  generated Antigravity wrapper (experimental)
playbooks/skills/<bucket>/<name>.md      →  shared workflow logic (authoritative)
.agents/skill-library.json               →  selectable skill library and pack metadata
.agents/skills.enabled.json              →  active profile/packs for this repo
.claude-plugin/plugin.json               →  generated active-skill manifest
```

Selectable skills live in `.agents/skill-library.json`, grouped into packs such as `core`, `ui`,
`task-management`, `github`, `personal`, and `platform-claude`. The active selection lives in
`.agents/skills.enabled.json`. `_base/scripts/sync-skill-selection.py` materializes that selection into
`.claude-plugin/plugin.json` and the runtime wrapper trees. Active runtime wrappers are generated
surfaces, not the durable source of truth.

Most wrappers point to the same playbook. **The playbook is the workflow source of truth.** Optional
inactive skills stay available through the library and playbooks but are not exposed to agents until
setup/re-setup activates their pack. The agent-only roles `implementer` and `reviewer` are not
invocable skills; their canonical behavior lives in `.claude/agents/`, `.codex/agents/`, the subagent
protocol, and the matching personality cards.

Useful selection commands:

```bash
./_base/scripts/sync-skill-selection.py --list
./_base/scripts/setup-agents.sh --skills-profile minimal
./_base/scripts/setup-agents.sh --skills-profile recommended
./_base/scripts/setup-agents.sh --all-skills
./_base/scripts/setup-agents.sh --skills core,ui,github
```

### Available skills

The table below lists the active skills for this template's default `recommended` selection. The full
optional library is listed by `./_base/scripts/sync-skill-selection.py --list`. Downstream projects
that add their own skills should list those in their own `README.md`, not here. Vendored Codex plugins
ship additional skills not listed here — `_base/plugins/superpowers/` (~14 skills: brainstorming,
dispatching-parallel-agents, writing-plans, executing-plans, test-driven-development,
systematic-debugging, etc.) and `_base/plugins/github/` (PR/issue/CI workflows). Those become
available when you run `./_base/plugins/install-codex-plugins.sh` (Codex) or load the equivalent plugin
in Claude Code.

<!-- BEGIN skills-table -->
<!-- This block is auto-generated by _base/scripts/gen-skills-table.sh from .claude-plugin/plugin.json — do not edit by hand. -->

| Skill | Bucket | Description |
|-------|--------|-------------|
| add-task | productivity | Create a full area-prefixed task in docs/tasks_manager/_todos/ with phases, acceptance criteria, related tests, priority, optional roadmap placement, and dates only when scheduling intent is explicit. Use when the user says "add task", "create task", "file a task", or "track this task". |
| align | productivity | Check a proposed feature or change against the project's PROJECT.md (vision, goals, scope, constraints) and report ALIGNED, NEEDS_CLARIFICATION, or OUT_OF_SCOPE. Use when the user wants Codex to validate alignment before starting non-trivial work or before planning. Requires PROJECT.md at the repo root. |
| audit-todos | productivity | Audit active task files against current repo state to find outdated, completed, obsolete, duplicated, or follow-up-ready work. Use when the user says "audit todos", "audit tasks", "review active tasks", or asks for periodic task backlog health checks. |
| capture-idea | productivity | Capture an idea into the inbox (docs/tasks_manager/_inbox/) as an I-NNN file with near-zero friction. Use whenever the user says "capture", "add to inbox", "note this idea", "jot down", or shares a feature/bug/idea they want recorded for later -- even if they don't explicitly ask to use a skill. |
| complete-task | productivity | Complete or cancel an active task: reconcile progress, fill completion harvest/summary, optionally squash task-owned commits, archive it, and sync ledgers. Use when the user says "complete task", "finish task", "close task", "cancel task", asks to archive a done task, or finds completed work still active. |
| diagnose | engineering | Disciplined diagnosis loop for hard bugs and performance regressions. Reproduce -> minimise -> hypothesise -> instrument -> fix -> regression-test. Use when user says "diagnose this" / "debug this", reports a bug, says something is broken/throwing/failing, or describes a performance regression. |
| execute-plan | engineering | Execute an approved task or implementation plan phase-by-phase, committing each completed phase and running repeated independent reviews. Use when the user says "execute plan", "execute-plan", or "/execute-plan", or points to docs/tasks_manager/_todos/<TASK>.md or docs/_plans/<slug>.md and wants it implemented. |
| frontend-design | misc | Create distinctive, production-grade frontend interfaces with high design quality and rendered verification. Use when the user asks to build web components, pages, apps, dashboards, games, or redesign/restyle UI. Avoids generic AI aesthetics and verifies responsive, accessible output. |
| handoff | productivity | Compact the current conversation into a handoff document so a fresh agent can pick up the work. Use when the user wants a session summary written to disk for later continuation, mentions "handing off", or is wrapping up a long session. |
| init | misc | Initialize project idea/task tracking structure. Use when the user wants Codex to set up docs/ with inbox, tasks, areas, durable plans, resources, archive, roadmap, and generated ledgers. |
| performance-optimization | engineering | Measure-first performance optimization -- profile to find the real hot path, record a baseline, change one thing, and re-measure before keeping it. Use when the user wants Codex to optimize performance, reduce latency or memory, speed something up, or asks "why is this slow?" for a known hot path. |
| planning-workflow | productivity | Seven-step pre-implementation planning workflow. Use when the user wants Codex to plan a non-trivial change before writing code -- multi-file features, multiple plausible approaches, or work that needs scope bounded. Includes a five-axis adversarial critique rubric for plan validation. |
| prd-to-plan | productivity | Turn a PRD into a multi-phase implementation plan using tracer-bullet vertical slices, saved as docs/_plans/<slug>.md. Use when the user wants Codex to break down a PRD, create an implementation plan, plan phases from a PRD, or mentions "tracer bullets". |
| prd-to-todos | productivity | Extract actionable tasks from a PRD and create area-prefixed task files. Use when the user wants Codex to convert a PRD into trackable tasks in docs/tasks_manager/_todos/. |
| prototype | engineering | Build a throwaway prototype before committing to a design: a runnable terminal app for logic/state questions or several UI variations on one route. Use when the user wants to prototype, test a data model or state machine, mock up UI options, or says "prototype this", "let me play with it", or "try a few designs". |
| roadmap | productivity | Maintain docs/tasks_manager/_roadmap.md -- the Urgent/Now/Next/Later/Someday ordering plus optional dated milestone headings. Use when the user wants to "plan the roadmap", "what's next", reprioritize/sequence work, schedule tasks, or refresh the roadmap. Distinct from per-change planning. |
| security-review-owasp | engineering | Apply current OWASP standards (Top 10:2025, ASVS 5.0, LLM Top 10 2025, Agentic AI 2026) when writing or reviewing code. Use when reviewing code for security issues, implementing auth/authz, handling user input, designing API endpoints, building AI agent systems, integrating LLMs/RAG, or discussing application security. |
| spec-workflow | engineering | Spec-driven planning and implementation loop for a non-trivial engineering item, producing specs/<slug>/ artifacts and review/fix passes. Use when the user asks to "spec it out", run a "spec workflow" or "spec-driven" process, or plan + build + review work too large for the default loop. Avoid trivial edits or exploratory spikes. |
| squash-workspace-commits | productivity | Squash completed workspace/task commits after validation while protecting unrelated or pushed history. Use when the user says "squash commits", "clean up commits", "squash task commits", or asks to compact agent phase commits after review. |
| subagent-protocol | productivity | Multi-agent coordination protocol with status vocabulary, dispatch format, and two-stage review. Use when the user wants Codex to dispatch subagents, coordinate multi-agent work, or review implementation output. |
| task-spec-workflow | engineering | Normalize an existing task or clear implementation idea into task-local Specification, Design, phases, acceptance criteria, tests, and Spec refs. Use when the user asks to spec a task, make a task implementation-ready, or plan task-manager-native spec-driven work before execute-plan. |
| tdd | engineering | Test-driven development with red-green-refactor loop. Use when the user wants Codex to build features or fix bugs using TDD, mentions "red-green-refactor", wants integration tests, or asks for test-first development. |
| tidy-repo | productivity | Inventory scattered TODOs, loose docs, and orphan files, then propose a non-destructive migration into docs/tasks_manager and docs/resources. Use when the user says "tidy this repo", "systematize", "clean up the mess", or "organize my tasks/docs". |
| triage-inbox | productivity | Review captured inbox ideas (docs/tasks_manager/_inbox/) and promote worthwhile ones into full area-prefixed tasks, or drop them. Use when the user says "triage inbox", "review the inbox", "process my ideas", "clear the inbox", or wants to turn captured ideas into actionable tasks. |
| ui-design-review | misc | Review rendered frontend UI for design quality, accessibility, responsiveness, interaction states, and implementation polish. Use when the user asks for UI review, design critique, visual QA, polish pass, responsive audit, accessibility check, or post-build frontend review. |

<!-- END skills-table -->

### Adding a new skill

1. Pick a bucket (`engineering`, `productivity`, `misc`, `personal`).
2. Create the playbook: `playbooks/skills/<bucket>/<name>.md`
3. Add metadata under `.agents/skill-library.json` `skills.<name>`.
4. Add the skill to one or more library packs in `.agents/skill-library.json`.
5. If it should be active in this repo, add its pack or name to `.agents/skills.enabled.json`, or run
   `./_base/scripts/setup-agents.sh --skills ...`.
6. Regenerate active manifests and wrappers: `./_base/scripts/sync-skill-selection.py --sync`.
7. Regenerate the active skills table: `./_base/scripts/gen-skills-table.sh`.
8. Validate consistency: `./_base/scripts/check-skills-sync.sh` and
   `./_base/scripts/check-antigravity-skills.sh` (fix any findings and re-run until clean).
9. For Codex, run `skills/install-codex-skills.sh` and restart Codex.

See `playbooks/skills/productivity/write-a-skill.md` for the full skill authoring guide.

### Validating skill/wrapper consistency

`_base/scripts/check-skills-sync.sh` verifies that the selected skill library is valid, generated
manifests/wrappers match `.agents/skills.enabled.json`, active wrappers are present, inactive runtime
wrappers are absent, the auto-generated skills table is up-to-date, and personalities are not exposed
as slash commands. It calls `sync-skill-selection.py --check` and `gen-skills-table.sh --check`, so
validation is read-only. Designed to be called by an agent in a loop:

```bash
./_base/scripts/check-skills-sync.sh
# Read each finding (line format: SEVERITY  CHECK_ID  PATH  [details]).
# Fix one or a batch, then re-run. Stop when output is "OK ...".
```

Severities: **BLOCKER** (missing/orphan files, broken references), **DRIFT** (out-of-sync metadata, mechanically fixable), **STYLE** (advisory thin-wrapper / convention violations). The script exits non-zero on BLOCKER or DRIFT; STYLE alone is allowed.
`_base/scripts/check-antigravity-skills.sh` separately verifies that generated `.agents/skills/`
wrappers match the active skill selection.

`_base/scripts/check-codex-plugins.sh` validates bundled Codex plugin manifests, referenced skill/app paths, plugin skill `SKILL.md` files, app JSON, optional MCP JSON, and declared interface assets. `_base/plugins/install-codex-plugins.sh` runs it before changing local symlinks or marketplace entries.

Template-owned scripts live under `_base/scripts/`, and template-owned bundled plugins live under `_base/plugins/`, so the root `scripts/` and `plugins/` directories remain available for downstream project tooling. Some helpers validate upstream-owned content, while task-system and setup helpers intentionally operate on the downstream repo state from their upstream-owned location. Downstream projects should not re-implement them; pull updates from the template and re-run.

`_base/scripts/setup-template-merge-rules.sh` configures the local Git merge drivers used by the root
`.gitattributes` template block. The drivers are template-aware: they apply the ownership rule only
when the merge or cherry-pick head comes from the `template` remote, and otherwise fall back to normal
three-way file merging. Run the setup script once during downstream setup, and rerun it if
`check-template-update.sh` reports missing merge rules.

`_base/scripts/check-template-update.sh` is the standard read-only, agent-runtime-independent
post-merge verifier for downstream repos. It prints the current `BASE_VERSION`, validates the template
merge rules, syntax-checks template shell scripts, runs the template validation checks including
generated Antigravity wrapper drift, exits non-zero when anything needs attention, and is designed for
an agent to run, fix reported failures, and rerun until green.

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
| Agent definitions | `.claude/agents/` native subagent dispatch (`implementer`, `reviewer`, `plan-critic`, `spec-validator`, `security-auditor`, `researcher`) | Use Codex multi-agent tools when available; otherwise roles run on the main thread under their cited personality + skill/convention |
| Hooks | `.claude/settings.json` PreToolUse | Codex approval policy (`suggest`/`auto-edit`/`full-auto`) |
| Per-directory overrides | Nested `AGENTS.md` in subdirectories | Not supported — root `AGENTS.md` only |

All workflow logic lives in `playbooks/` (shared). Platform-specific features in `.claude/`, `skills/`, and `_base/plugins/` are additive — a Codex user reading only `AGENTS.md` + `_base/AGENTS.md` + `playbooks/` + `skills/` + `_base/plugins/` gets the full picture.

Antigravity (`agy`) is an experimental adapter, not an equal primary runtime. Its only committed
workspace surface is `.agents/skills/`, generated from `.agents/skills.enabled.json`; there is no
Antigravity plugin bundle, manifest schema change, native subagent setup, or hook setup in this
template. Gemini CLI is mentioned only as compatibility or migration context where upstream tools or
`agy plugin import` reference it; this template does not ship or maintain Gemini runtime files.

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

## Using with Antigravity (`agy`, experimental)

Antigravity wrappers are generated into `.agents/skills/` from the active skill selection and
playbooks. They are intentionally thin so this adapter can be removed without touching Claude/Codex
wrappers, playbooks, plugin manifests, task conventions, or repo contracts.

```bash
./_base/scripts/setup-agents.sh --antigravity-only
# Then restart or reopen agy in this repo
```

For manual/debugging use:

```bash
./_base/scripts/gen-antigravity-skills.sh
./_base/scripts/check-antigravity-skills.sh
```

Removal path:

```bash
rm -rf .agents/skills
rm _base/scripts/gen-antigravity-skills.sh
rm _base/scripts/check-antigravity-skills.sh
```

Then delete the small Antigravity references from setup/check docs and scripts.

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
| `.agents/skill-library.json` and `.agents/skills.enabled.json` | Both | Optional skill library and active profile/packs |
| `.claude/` | Claude Code | Skills, native subagents, hook scripts, settings |
| `skills/` | Codex | Thin wrappers + `install-codex-skills.sh` |
| `.agents/skills/` | Antigravity (experimental) | Generated wrappers only; regenerate from `.agents/skills.enabled.json` |
| `_base/scripts/setup-agents.sh` | Both | One-command skill/plugin validation and install/refresh for Claude Code and Codex; `--antigravity-only` regenerates experimental `agy` wrappers |
| `_base/plugins/` | Both | Vendored plugins, `install-codex-plugins.sh`, `install-claude-plugins.sh`, `bootstrap-third-party.sh` |
| `_base/project.env.example` | Both (optional) | Copy to `project.env` at the repo root (`cp _base/project.env.example project.env`) to override default install paths |
| `_base/PROJECT.md.template` | Both (optional) | Copy to `PROJECT.md` at the repo root (`cp _base/PROJECT.md.template PROJECT.md`) and fill in to enable the `/align` skill for feature-level alignment gating |
| `_base/repos.project.example.md` | Both (optional) | Copy to `.config/repos.project.md` and edit when the downstream project needs a committed repo registry |
| `_base/repos.map.example` | Both (optional, local-only) | Copy to `.local/repos.map` and edit with machine-local absolute checkout directory paths; `.local/` is gitignored |

After copying or pulling template updates, run the one-command setup:

```bash
./_base/scripts/setup-agents.sh
```

In an interactive terminal it first asks which optional skill profile or packs to activate. In
non-interactive runs it keeps the committed `.agents/skills.enabled.json` selection unless you pass
`--skills-profile`, `--skills`, or `--all-skills`. It then validates the skill catalog, installs or
refreshes Codex skills and plugins, links Claude Code skills globally, and installs or refreshes Claude
Code plugins. The command is idempotent; run it again after each template update. Restart Codex and
Claude Code afterwards so they reload skills and plugins. The lower-level installers remain available
for advanced/manual use. To set up only one primary runtime, use
`./_base/scripts/setup-agents.sh --codex-only` or `./_base/scripts/setup-agents.sh --claude-only`. To
refresh only the experimental Antigravity wrappers, use `./_base/scripts/setup-agents.sh
--antigravity-only`.

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
./_base/scripts/setup-template-merge-rules.sh
```

Commit the resulting `.gitattributes` change in the downstream repo. The script also writes local Git
config for the two custom merge drivers, which is intentionally not committed.

### Pulling updates from the template

```bash
git fetch template
git log --oneline HEAD..template/master    # preview what's new upstream
git diff HEAD..template/master -- _base/CHANGELOG.md   # human-readable summary + per-change downstream impact
./_base/scripts/setup-template-merge-rules.sh --check   # if this fails, run it without --check and commit .gitattributes
git merge template/master                  # or: git cherry-pick <commit>
./_base/scripts/check-template-update.sh   # read-only verification after the merge
```

Always check `_base/CHANGELOG.md` before merging — each entry includes a **Downstream impact** line
that flags expected conflicts, new conventions, or behavior changes. Keep
`./_base/scripts/setup-template-merge-rules.sh --check` green before template merges so Git can apply
the ownership rules automatically. Use `merge` when you want everything; use `cherry-pick` when you
only want specific commits (e.g. a new skill but not a hook change you've customized). After the merge,
an agent can run `./_base/scripts/check-template-update.sh`, fix any reported failures, and rerun it
until it passes.

### File conventions for downstream projects

Each repo file falls into one of three buckets:

**Downstream-owned** (each project writes its own; never conflicts on pulls):

- `README.md` — describes the project, links to `_base/README.md`.
- `AGENTS.md` — entrypoint auto-loaded by agents; instructs them to read `_base/AGENTS.md` and then applies any project-specific overrides.
- `.gitattributes` — contains the managed agents-template merge-rule block plus any project-specific
  attributes outside that block.
- `.config/repos.project.md` (optional) — committed repo registry created from `_base/repos.project.example.md` when
  a project needs stable repo slugs, branch/work policy, and task `Repos` metadata.
- `workbooks/` — workbook bundles, one folder per workbook. Seeded from `_base/workbooks/README.md`,
  then owned by the downstream project.
- `tools/python/` — optional downstream-owned Python tooling environments. Commit uv metadata files
  such as `pyproject.toml`, `uv.lock`, and `.python-version` once dependencies exist; never commit
  `.venv/`.

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
- `.creds/` — never committed; local credential files for agent/tool use when a task requires them.
- `.venv/` — never committed; local Python virtual environment.
- `tools/python/.venv/` — never committed; local uv-managed Python tooling environment.
- `.local/repos.map` — never committed; machine-local checkout paths for repo slugs in `.config/repos.project.md`.
- `.local/runbooks/` — never committed; machine-local placeholder bindings for sanitized runbooks.
- `PROJECT.md` — downstream-owned alignment doc, if seeded from `_base/PROJECT.md.template`. The template flows in cleanly; the seeded `PROJECT.md` is the project's own and is not touched by template pulls.

### Template merge rules

The root `.gitattributes` managed block turns the ownership split into Git merge behavior:

- `template-keep-upstream` accepts the template remote's version for `_base/**`.
- `template-keep-local` keeps the downstream version for `AGENTS.md`, `README.md`, seeded docs,
  workbook bundles, `tools/python/`, `PROJECT.md`, `CONTEXT.md`, `CHANGELOG.md`, `LICENSE`, and
  `.config/repos.project.md`.
- mixed paths such as `playbooks/`, `skills/`, and `.claude/settings.json` are intentionally not
  automated because downstream forks need human judgment.

These custom drivers detect Git's `GITHEAD_*`/`GIT_REFLOG_ACTION` merge environment, with
`MERGE_HEAD`/`CHERRY_PICK_HEAD` as a fallback, against refs under the `template` remote. For ordinary
project branch merges, they run Git's normal three-way file merge instead of forcing either side. The
driver commands live in local Git config, not in committed files, so each checkout must run:

```bash
./_base/scripts/setup-template-merge-rules.sh
```

Commit `.gitattributes` if the script changes it. Do not commit `.git/config`.

### Agent instructions for downstream projects

When operating in a project that was seeded from this template, agents should:

1. On request to "update from the template" or "pull template updates", run `git fetch template` and show the user the diff before merging.
2. Never push to the `template` remote. The push URL is disabled by convention; if it is not, treat any push there as out of scope.
3. If the `template` remote is missing in a project that clearly originated from this template (presence of `AGENTS.md` + `_base/`, `playbooks/`, `.claude/skills/`), offer to add it with the one-time setup commands above.
4. Never edit anything under `_base/` in a downstream project. Suggested base-contract changes belong upstream in the template repo itself.
5. Before template merges, run `./_base/scripts/setup-template-merge-rules.sh --check`; if it fails,
   run it without `--check`, commit `.gitattributes` if changed, then retry the merge.
6. If the base changelog describes new or changed downstream-owned formats, seeded docs, task metadata,
   project-slot files, or local setup conventions, ask whether the user wants to migrate the downstream
   repo to the updated base format. Treat that migration as a separate user-approved step, not as an
   automatic side effect of merging `_base/**`.

## Recommended adoption pattern

### Minimum adoption

- place `AGENTS.md` at the project root and copy the `_base/` directory alongside it
- copy the skills and plugins you need

### Stronger adoption

- use `manager.md`, `builder.md`, `tester.md`, `critic.md`, and `reviewer.md` as explicit passes or sub-agent roles
- copy the files in `playbooks/templates/` for durable progress, task, and decision state
- require agents to use conventional commit summaries plus a commit body
- define branch mode up front: `default-branch` or `same-branch` for template-inherited downstream
  repos, and `task-branch` only where a project explicitly wants per-task branches
- commit `.config/repos.project.md` for multi-repo projects so `execute-plan` can verify branch/work
  mode before making phase commits
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
In working/product repos, use the current/default branch unless task-branch mode is explicit.
Commit each coherent, reviewable slice with a conventional summary line and a body explaining what changed and why.
For tracked tasks, update the task file progress and execution log before treating a phase as complete.
After a downstream task is complete and reviewed, squash only that task's own step commits if cleanup is desired.
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

The skill creates `specs/<slug>/` at the project root and populates it with four artifacts (`spec.md`, `design.md`, `tasks.md`, `review.md`). Phase 2 dispatches implementer subagents per task when the runtime supports subagents; otherwise the main agent applies the implementer role explicitly. Phase 3 runs a reviewer pass (two-stage: spec compliance + code quality) and appends to `review.md`. On a failed review, fix tasks are appended to `tasks.md` and the loop runs again. Full mechanics in [`playbooks/skills/engineering/spec-workflow.md`](../playbooks/skills/engineering/spec-workflow.md).

### Example 6: task-native specs and system mapping

Use [`task-spec-workflow`](../playbooks/skills/engineering/task-spec-workflow.md) when an ordinary task
needs a task-local spec before implementation, and use
[`map-system`](../playbooks/skills/engineering/map-system.md) when the project needs a top-level
repo/capability picture.

```text
Use /task-spec-workflow on T-004.
Resolve Spec refs and add task-local Specification, Design, acceptance criteria, and tests.
Stop before implementation.

Use /map-system for the runtime-platform repos.
Refresh docs/resources/system-map.md and link detailed area docs.
```

Task-local specs are planned intent until closeout. Durable specs and system-map rows must carry
status, and only `implemented` or evidence-backed `partially-implemented` specs may be treated as
current system behavior.

## Update workflow

1. Run `playbooks/meta/UPDATE_PLAN.md`.
2. Refresh `playbooks/meta/RESEARCH_SNAPSHOT.md`.
3. Update `_base/AGENTS.md` and `playbooks/personalities/` only where evidence supports a change.
4. Review the repo for clarity and portability.
5. Update `_base/README.md` examples so adoption stays easy.
