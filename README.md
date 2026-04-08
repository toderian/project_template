# Agents Template

Template repository for portable agent behavior contracts and reusable skills in any development project.

This repo is designed to work with both **Claude Code** and **OpenAI Codex**. Copy it into a project or use it as a submodule.

## What is in the repo

```text
.
├── AGENTS.md                              # Core agent operating contract
├── README.md
├── LICENSE
│
├── playbooks/                             # Shared workflow logic (single source of truth)
│   ├── <skill-name>.md                    # Playbook per skill
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
playbooks/<name>.md             →  shared workflow logic (authoritative)
```

Both wrappers point to the same playbook. **The playbook is the single source of truth.** When changing a workflow, update the playbook first; keep the wrappers thin.

### Available skills

| Skill | Description |
|-------|-------------|
| design-an-interface | Design software interfaces |
| implementer | Act as an implementer for a single task slice |
| edit-article | Edit and improve articles |
| git-guardrails-claude-code | Git safety hooks for Claude Code |
| github-triage | Label-based GitHub issue triage with grilling sessions |
| grill-me | Interactive grilling/quiz sessions |
| improve-codebase-architecture | Codebase architecture improvements |
| migrate-to-shoehorn | Shoehorn migration |
| obsidian-vault | Obsidian vault operations |
| prd-to-issues | Convert PRDs to GitHub issues |
| prd-to-plan | Convert PRDs to implementation plans |
| qa | Quality assurance review |
| request-refactor-plan | Refactoring plans |
| reviewer | Two-stage review (spec compliance + code quality) |
| scaffold-exercises | Scaffold learning exercises |
| setup-pre-commit | Set up pre-commit hooks |
| subagent-protocol | Multi-agent coordination protocol |
| tdd | Test-driven development |
| triage-issue | Investigate bugs and file TDD fix plans |
| ubiquitous-language | Domain language definition |
| write-a-prd | Write product requirement documents |
| write-a-skill | Create new skills |

### Adding a new skill

1. Create the playbook: `playbooks/<name>.md`
2. Create the Codex wrapper: `skills/<name>/SKILL.md`
3. Create the Claude wrapper: `.claude/skills/<name>/SKILL.md`
4. For Codex, run `skills/install-codex-skills.sh` and restart Codex

See `playbooks/write-a-skill.md` for the full skill authoring guide.

## Platform support

| Feature | Claude Code | Codex |
|---------|------------|-------|
| AGENTS.md | Auto-loaded | Auto-loaded |
| Skills (slash commands) | `.claude/skills/` auto-discovered | `skills/` via `install-codex-skills.sh` |
| Agent definitions | `.claude/agents/` native subagent dispatch | `skills/implementer/`, `skills/reviewer/` as behavioral skills |
| Hooks | `.claude/settings.json` PreToolUse | Codex approval policy (`suggest`/`auto-edit`/`full-auto`) |
| Per-directory overrides | Nested `AGENTS.md` in subdirectories | Not supported — root `AGENTS.md` only |

All workflow logic lives in `playbooks/` (shared). Platform-specific features in `.claude/` and `skills/` are additive — a Codex user reading only `AGENTS.md` + `playbooks/` + `skills/` gets the full picture.

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

Codex skill metadata:

```yaml
---
name: skill-name
description: What it does. Use when [triggers].
---
```

## Quick start

### Option 1: copy into a repo

Copy these into the target project:

- `AGENTS.md`
- `playbooks/` (includes personalities, templates, and meta docs)
- `skills/`, `.claude/skills/`

### Option 2: use as a submodule

```bash
git submodule add <this-repo-url> agent-template
```

Then reference the files from the root project or symlink the chosen artifacts into place.

## Recommended adoption pattern

### Minimum adoption

- place `AGENTS.md` at the project root
- copy the skills you need

### Stronger adoption

- use `manager.md`, `builder.md`, `tester.md`, `critic.md`, and `reviewer.md` as explicit passes or sub-agent roles
- copy the files in `playbooks/templates/` for durable progress, task, and decision state
- require agents to use conventional commit summaries plus a commit body
- rerun `playbooks/meta/UPDATE_PLAN.md` whenever you change the project's agent doctrine

## Examples

### Example 1: single-agent task

```text
Read AGENTS.md and solve this task as one agent.
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
Update playbooks/meta/RESEARCH_SNAPSHOT.md, AGENTS.md, and README examples together.
```

## Update workflow

1. Run `playbooks/meta/UPDATE_PLAN.md`.
2. Refresh `playbooks/meta/RESEARCH_SNAPSHOT.md`.
3. Update `AGENTS.md` and `playbooks/personalities/` only where evidence supports a change.
4. Review the repo for clarity and portability.
5. Update README examples so adoption stays easy.
