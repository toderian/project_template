# Agents Template

Template repository for portable agent behavior contracts in any development project.

The goal is not to store one big prompt. The goal is to store a small set of durable artifacts that teach agents how to work well in real repos:

- reason from first principles
- work in manager -> builder -> tester -> critic -> reviewer loops
- prefer evidence over fluency
- stay concise and operational
- improve continuously through dated research refreshes

This repo is intended to be copied into a project or used as a submodule.

## What is in the repo

```text
.
├── AGENTS.md
├── AGENTS_UPDATE_PLAN.md
├── README.md
├── RESEARCH_SNAPSHOT.md
├── templates/
│   ├── AGENT_DECISIONS.template.md
│   ├── AGENT_PROGRESS.template.md
│   └── AGENT_TASKS.template.json
└── personalities/
    ├── builder.md
    ├── critic.md
    ├── manager.md
    ├── researcher.md
    ├── reviewer.md
    └── tester.md
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

This is intentionally simple. Recent research and engineering writeups keep pointing to the same pattern: simple, explicit loops beat magical prompt complexity.

## Quick start

### Option 1: copy into a repo

Copy these files into the target project:

- `AGENTS.md`
- `personalities/`
- optionally `AGENTS_UPDATE_PLAN.md` and `RESEARCH_SNAPSHOT.md` if the project will evolve its agent doctrine

### Option 2: use as a submodule

```bash
git submodule add <this-repo-url> agent-template
```

Then reference the files from the root project documentation or symlink the chosen artifacts into place.

## Recommended adoption pattern

### Minimum adoption

- place `AGENTS.md` at the project root
- tell agents to follow it by default
- keep the role cards available for larger tasks

### Stronger adoption

- use `manager.md`, `builder.md`, `tester.md`, `critic.md`, and `reviewer.md` as explicit passes or sub-agent roles
- copy the files in `templates/` if the project wants durable progress, task, and decision state
- require agents to use conventional commit summaries plus a commit body when asked to commit or push
- rerun `AGENTS_UPDATE_PLAN.md` whenever you change the project’s agent doctrine
- update `RESEARCH_SNAPSHOT.md` so future edits are anchored to dated evidence

## Examples

### Example 1: single-agent task

Use one agent, but force it through the full loop:

```text
Read AGENTS.md and solve this task as one agent.
Work sequentially as manager, builder, tester, critic, and reviewer.
Do not stop at the first plausible answer.
Keep the final output concise and evidence-based.
```

### Example 2: multi-role task in a larger repo

Use the role cards explicitly:

```text
Manager: frame the task, define done, and split the work.
Builder: implement the smallest useful change.
Tester: verify behavior and regressions.
Critic: challenge assumptions and propose a better version.
Reviewer: decide whether the result is ready to merge.
If the critic or tester finds a real problem, loop again.
```

### Example 3: updating the template itself

When changing how agents should behave:

```text
Use researcher.md.
Rerun AGENTS_UPDATE_PLAN.md.
Check the latest primary sources.
Update RESEARCH_SNAPSHOT.md, AGENTS.md, and README examples together.
Do not promote a new pattern into the template unless the evidence is strong and portable.
```

### Example 4: commit and push behavior

When asking an agent to finalize work:

```text
If you commit, use a conventional summary line such as feat:, fix:, or chore:.
Always include a commit body that explains what changed and why.
Do not push a one-line commit message.
```

## Why this repo looks like this

The current structure reflects recent evidence from Anthropic, OpenAI, and foundational agent papers:

- iterative critique/refinement still matters
- actor-critic loops work best when the critic is backed by tests or other external checks
- long-running agents need durable handoffs and incremental progress
- multi-agent systems help only when the work is genuinely parallelizable
- evaluation quality matters more than leaderboard aesthetics
- benchmark scores need skepticism because contamination, grader flaws, and infra setup can distort results

See `RESEARCH_SNAPSHOT.md` for the dated source list and current conclusions.

## Update workflow

1. Run `AGENTS_UPDATE_PLAN.md`.
2. Refresh `RESEARCH_SNAPSHOT.md`.
3. Update `AGENTS.md` and `personalities/` only where evidence supports a change.
4. Review the repo for clarity and portability.
5. Update README examples so adoption stays easy.
