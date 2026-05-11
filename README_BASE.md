# Agents Template — Base

> **This is `README_BASE.md`**: the authoritative, shared base documentation for the agents template.
> The repo-level `README.md` extends this file. Downstream projects seeded from this template should keep `README_BASE.md` exactly as inherited (so it merges cleanly on `git fetch template && git merge`) and write their own `README.md` that links here.

Template repository for portable agent behavior contracts and reusable skills in any development project.

This repo is designed to work with both **Claude Code** and **OpenAI Codex**. Copy it into a project, use it as a submodule, or seed a new project from it and keep it wired up as a `template` git remote so you can pull future improvements in (see [Staying in sync with the template](#staying-in-sync-with-the-template)).

**Canonical URL:** `git@github.com:toderian/project_template.git`

## What is in the repo

```text
.
├── AGENTS.md                              # Downstream-owned entrypoint; loads AGENTS_BASE.md
├── AGENTS_BASE.md                         # Upstream-owned base operating contract
├── README.md                              # Downstream-owned README; links to README_BASE.md
├── README_BASE.md                         # Upstream-owned base documentation (this file)
├── LICENSE
│
├── playbooks/                             # Shared workflow logic (single source of truth)
│   ├── skills/                            # Skill playbooks
│   │   ├── <skill-name>.md
│   │   ├── tdd/                           # Complex skill subdirectories
│   │   └── github-triage/
│   ├── personalities/                     # Role cards for multi-pass workflows
│   │   ├── manager.md, builder.md, tester.md
│   │   ├── critic.md, reviewer.md, researcher.md
│   ├── templates/                         # Durable artifacts for long-running tasks
│   │   ├── AGENT_TASKS.template.json
│   │   ├── AGENT_PROGRESS.template.md
│   │   └── AGENT_DECISIONS.template.md
│   └── meta/                              # Template maintenance
│       ├── UPDATE_PLAN.md
│       └── RESEARCH_SNAPSHOT.md
│
├── skills/                                # Codex skill wrappers (thin)
│   ├── <skill-name>/SKILL.md
│   └── install-codex-skills.sh
├── plugins/                               # Optional Codex plugins
│   ├── <plugin-name>/.codex-plugin/plugin.json
│   └── install-codex-plugins.sh
│
└── .claude/
    ├── skills/                            # Claude Code skill wrappers (thin)
    │   └── <skill-name>/SKILL.md
    ├── agents/                            # Claude Code subagent definitions
    │   ├── implementer.md
    │   └── reviewer.md
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

## Skills and playbooks

Skills are reusable agent capabilities invoked by name (e.g. `/tdd`, `/qa`, `/grill-me`).

### Architecture

```
skills/<name>/SKILL.md          →  thin Codex wrapper
.claude/skills/<name>/SKILL.md  →  thin Claude Code wrapper
playbooks/skills/<name>.md      →  shared workflow logic (authoritative)
```

Both wrappers point to the same playbook. **The playbook is the single source of truth.** When changing a workflow, update the playbook first; keep the wrappers thin.

### Available skills

The table below lists the skills authored in this template. Vendored Codex plugins ship additional skills not listed here — `plugins/superpowers/` (~14 skills: brainstorming, dispatching-parallel-agents, writing-plans, executing-plans, test-driven-development, systematic-debugging, etc.) and `plugins/github/` (PR/issue/CI workflows). Those become available when you run `./plugins/install-codex-plugins.sh` (Codex) or load the equivalent plugin in Claude Code.

| Skill | Description |
|-------|-------------|
| design-an-interface | Design software interfaces |
| implementer | Act as an implementer for a single task slice |
| edit-article | Edit and improve articles |
| frontend-design | Build distinctive frontend interfaces (imported from Anthropic's frontend-design plugin) |
| git-guardrails-claude-code | Git safety hooks for Claude Code |
| github-triage | Label-based GitHub issue triage with grilling sessions |
| grill-me | Interactive grilling/quiz sessions |
| improve-codebase-architecture | Codebase architecture improvements |
| init | Initialize project todo tracking structure |
| migrate-to-shoehorn | Shoehorn migration |
| migration-safety | Safe DB schema migrations (PG/MySQL/SQLite) — locks, backfills, rollbacks (adapted from OmexIT) |
| obsidian-vault | Obsidian vault operations |
| prd-to-issues | Convert PRDs to GitHub issues |
| prd-to-plan | Convert PRDs to implementation plans |
| prd-to-todos | Extract todos from a PRD into docs/_todos/ |
| qa | Quality assurance review |
| request-refactor-plan | Refactoring plans |
| reviewer | Two-stage review (spec compliance + code quality) |
| scaffold-exercises | Scaffold learning exercises |
| security-review-owasp | OWASP Top 10:2025, ASVS 5.0, LLM Top 10, Agentic AI 2026 review (vendored from agamm/claude-code-owasp) |
| setup-pre-commit | Set up pre-commit hooks |
| subagent-protocol | Multi-agent coordination protocol |
| tdd | Test-driven development |
| triage-issue | Investigate bugs and file TDD fix plans |
| ubiquitous-language | Domain language definition |
| write-a-prd | Write product requirement documents |
| write-a-skill | Create new skills |

### Adding a new skill

1. Create the playbook: `playbooks/skills/<name>.md`
2. Create the Codex wrapper: `skills/<name>/SKILL.md`
3. Create the Claude wrapper: `.claude/skills/<name>/SKILL.md`
4. For Codex, run `skills/install-codex-skills.sh` and restart Codex

See `playbooks/skills/write-a-skill.md` for the full skill authoring guide.

## Platform support

| Feature | Claude Code | Codex |
|---------|------------|-------|
| AGENTS.md (+ AGENTS_BASE.md) | Auto-loaded; loads `AGENTS_BASE.md` by instruction | Auto-loaded; loads `AGENTS_BASE.md` by instruction |
| Skills (slash commands) | `.claude/skills/` auto-discovered | `skills/` via `install-codex-skills.sh` |
| Plugins | Not applicable | `plugins/` via `install-codex-plugins.sh` and local marketplace entries |
| Agent definitions | `.claude/agents/` native subagent dispatch | `skills/implementer/`, `skills/reviewer/` as behavioral skills |
| Hooks | `.claude/settings.json` PreToolUse | Codex approval policy (`suggest`/`auto-edit`/`full-auto`) |
| Per-directory overrides | Nested `AGENTS.md` in subdirectories | Not supported — root `AGENTS.md` only |

All workflow logic lives in `playbooks/` (shared). Platform-specific features in `.claude/`, `skills/`, and `plugins/` are additive — a Codex user reading only `AGENTS.md` + `AGENTS_BASE.md` + `playbooks/` + `skills/` + `plugins/` gets the full picture.

## Using with Claude Code

Claude Code discovers skills automatically from `.claude/skills/`. No installation needed — open the project and skills are available as slash commands.

Claude-specific skill metadata:

```yaml
---
name: skill-name
description: What it does. Use when [triggers].
disable-model-invocation: true   # hand off to playbook, don't generate
---
```

## Using with Codex

Codex skills live in `skills/` and must be symlinked into `~/.codex/skills/`:

```bash
./skills/install-codex-skills.sh
# Then restart Codex
```

Codex plugins live in `plugins/` and use the `.codex-plugin/plugin.json`
manifest layout:

```bash
./plugins/install-codex-plugins.sh
# Then restart Codex
```

The plugin installer symlinks repo plugins into `~/plugins/` by default and
adds local marketplace entries to `~/.agents/plugins/marketplace.json`.

Codex skill metadata:

```yaml
---
name: skill-name
description: What it does. Use when [triggers].
---
```

## Third-party plugins (own installers)

Some upstream tools ship multi-platform installers and don't fit the
`playbooks/` + dual-wrapper convention. They're not vendored — instead,
`plugins/bootstrap-third-party.sh` runs (or documents) their native install
paths:

| Tool | What it adds | Install path |
|------|--------------|--------------|
| `get-shit-done-cc` | Spec-driven dev workflow (researchers/planners/executors) | `npx get-shit-done-cc --claude --global` and `--codex --global` |
| `context-mode` | MCP server + hooks that sandbox tool output (~98% context savings on Claude, ~60% on Codex) | `/plugin marketplace add mksglu/context-mode` |
| `claude-mem` | Cross-session memory via MCP; ships both `.claude-plugin/` and `.codex-plugin/` | `/plugin marketplace add thedotmack/claude-mem` |

Run `./plugins/bootstrap-third-party.sh` to install the npm-based ones and
print the marketplace commands for the others. Toggle each section with env
vars (`INSTALL_GSD`, `INSTALL_CONTEXT_MODE`, `INSTALL_CLAUDE_MEM`).

## Quick start

### Option 1: copy into a repo

Copy these into the target project (then run the Codex installers if you use Codex):

| Artifact | Required for | Notes |
|----------|--------------|-------|
| `AGENTS.md` | Both | Auto-loaded entrypoint; downstream-owned (project-specific overrides go here) |
| `AGENTS_BASE.md` | Both | Base operating contract; upstream-owned (do not edit downstream) |
| `playbooks/` | Both | Authoritative workflow logic, role cards, templates |
| `.claude/` | Claude Code | Skills, native subagents, hook scripts, settings |
| `skills/` | Codex | Thin wrappers + `install-codex-skills.sh` |
| `plugins/` | Codex (optional) | Vendored plugins + `install-codex-plugins.sh` + `bootstrap-third-party.sh` |
| `project.env.example` | Both (optional) | Copy to `project.env` to override default install paths |

After copying, Claude Code is ready immediately. For Codex, run:

```bash
./skills/install-codex-skills.sh
./plugins/install-codex-plugins.sh
./plugins/bootstrap-third-party.sh   # optional third-party stack
# Then restart Codex
```

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
#    keep README_BASE.md as-is so it can be cleanly updated from upstream.
#    Your README.md should describe your project and link to README_BASE.md.
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

This project extends the agents template — see [`README_BASE.md`](./README_BASE.md)
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
git merge template/master                  # or: git cherry-pick <commit>
```

Use `merge` when you want everything; use `cherry-pick` when you only want specific commits (e.g. a new skill but not a hook change you've customized).

### File conventions for downstream projects

Each repo file falls into one of three buckets:

**Downstream-owned** (each project writes its own; never conflicts on pulls):

- `README.md` — describes the project, links to `README_BASE.md`.
- `AGENTS.md` — entrypoint auto-loaded by agents; instructs them to read `AGENTS_BASE.md` and then applies any project-specific overrides.

**Upstream-owned** (do not edit downstream; flows in cleanly from `git fetch template && git merge`):

- `README_BASE.md` — base documentation.
- `AGENTS_BASE.md` — base operating contract.

**Mixed** (manual merge required):

- `.claude/settings.json` — merge hook entries by hand; don't blindly accept upstream.
- `playbooks/skills/*` and `skills/*` / `.claude/skills/*` — accept upstream for skills you haven't customized; keep downstream for skills you've forked.
- `project.env` — never committed; not a conflict source.

### Agent instructions for downstream projects

When operating in a project that was seeded from this template, agents should:

1. On request to "update from the template" or "pull template updates", run `git fetch template` and show the user the diff before merging.
2. Never push to the `template` remote. The push URL is disabled by convention; if it is not, treat any push there as out of scope.
3. If the `template` remote is missing in a project that clearly originated from this template (presence of `AGENTS.md` + `AGENTS_BASE.md`, `playbooks/`, `.claude/skills/`), offer to add it with the one-time setup commands above.
4. Never edit `AGENTS_BASE.md` or `README_BASE.md` in a downstream project. Suggested base-contract changes belong upstream in the template repo itself.

## Recommended adoption pattern

### Minimum adoption

- place `AGENTS.md` and `AGENTS_BASE.md` at the project root
- copy the skills and plugins you need

### Stronger adoption

- use `manager.md`, `builder.md`, `tester.md`, `critic.md`, and `reviewer.md` as explicit passes or sub-agent roles
- copy the files in `playbooks/templates/` for durable progress, task, and decision state
- require agents to use conventional commit summaries plus a commit body
- rerun `playbooks/meta/UPDATE_PLAN.md` whenever you change the project's agent doctrine

## Examples

### Example 1: single-agent task

```text
Read AGENTS.md (and AGENTS_BASE.md, which it loads) and solve this task as one agent.
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
If you commit, use a conventional summary line such as feat:, fix:, or chore:.
Always include a commit body that explains what changed and why.
Do not push a one-line commit message.
```

### Example 4: updating the template itself

```text
Use researcher.md.
Rerun playbooks/meta/UPDATE_PLAN.md.
Check the latest primary sources.
Update playbooks/meta/RESEARCH_SNAPSHOT.md, AGENTS_BASE.md, and README_BASE.md examples together.
```

## Update workflow

1. Run `playbooks/meta/UPDATE_PLAN.md`.
2. Refresh `playbooks/meta/RESEARCH_SNAPSHOT.md`.
3. Update `AGENTS_BASE.md` and `playbooks/personalities/` only where evidence supports a change.
4. Review the repo for clarity and portability.
5. Update `README_BASE.md` examples so adoption stays easy.
