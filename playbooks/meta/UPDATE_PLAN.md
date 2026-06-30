# Update Plan

Repeatable research and template-refresh plan for this repository.

Last executed: 2026-07-01.

## Purpose

Keep this template aligned with the latest useful research and operational lessons on agent behavior for development work, without turning the repo into vendor-specific prompt cargo cult.

This plan exists so future updates can be rerun with the same discipline:

- search broadly enough to catch real advances
- prefer primary sources
- separate signal from hype
- only promote findings that improve a portable dev-project template

## When to rerun

Rerun this plan when any of the following is true:

- a core behavior file is being changed (`_base/AGENTS.md`, `playbooks/personalities/`, research snapshot, `_base/README.md` examples)
- a major new agent paper, benchmark, or engineering post is released
- a new failure pattern is observed in real projects using this template
- at least 30 days have passed since the last meaningful review

## Research questions

Every run should answer these questions:

1. What new evidence exists for how agents should reason, plan, critique, and refine?
2. What orchestration patterns actually improve results, and when do they fail?
3. What changed in best practice for coding-agent evaluation, harness design, or benchmark reliability?
4. What changed in context engineering, long-running execution, or memory/handoff design?
5. What changed in tool design, safety, permissioning, or human escalation?
6. Which findings are portable to any dev repo, and which are provider-specific?

## Source hierarchy

Prefer sources in this order:

1. official engineering and research posts from model providers
2. official documentation from provider platforms
3. benchmark maintainers and official benchmark docs
4. peer-reviewed papers or arXiv papers from the original authors
5. practitioner writeups only as secondary corroboration

Reject or downweight:

- unsourced benchmark screenshots
- derivative summaries without links to originals
- highly product-specific tactics that do not generalize

## Required source mix per run

Each refresh should review at minimum:

- 2 recent provider engineering posts from the last 6 months
- 1 evaluation or benchmark integrity source
- 1 source on long-running or multi-agent orchestration
- 1 source on tools, context, or harness design
- 2 enduring/foundational sources for comparison

## Query pack

Use some variation of these search queries each run.

### Provider engineering

- `site:anthropic.com/engineering agents evals coding context engineering`
- `site:anthropic.com/engineering multi-agent long-running agents tools`
- `site:openai.com agents coding benchmark evals official`
- `site:developers.openai.com \"agent evals\" OR \"trace grading\"`

### Benchmarks and evaluation integrity

- `site:openai.com SWE-bench Verified Pro coding benchmark official`
- `site:anthropic.com/engineering benchmark eval integrity coding`
- `site:swebench.com leaderboard benchmark docs`

### Research papers

- `site:arxiv.org llm agent actor critic critique coding`
- `site:arxiv.org self-refine reflexion process reward model agents`
- `site:arxiv.org coding agents evaluation benchmark software engineering`

## Triage rubric

Score each candidate source on these dimensions from 0 to 2:

- recency: how recent is it relative to the current run
- evidence quality: benchmark, experiment, operational detail, or only opinion
- practical transfer: can the finding change this template
- generality: does it apply to many dev repos, not only one product stack

Promote only findings that score well overall and survive contradiction checks.

## Execution workflow

### Step 1: Collect

- gather candidate sources from the last 12 months
- add a small set of foundational papers for comparison
- record publication dates

### Step 2: Filter

- keep only primary sources or official benchmark materials
- remove duplicates and near-duplicates
- classify each item by theme: orchestration, evaluation, context, tools, safety, critique/refinement

### Step 3: Extract findings

For each kept source, record:

- the main claim
- the evidence behind it
- what it changes for this repo, if anything
- whether the finding is durable principle or time-sensitive practice

### Step 4: Resolve conflicts

When sources disagree:

- prefer controlled evaluations over intuition
- prefer operational writeups over abstract pattern lists
- prefer simpler workflows until complexity clearly wins
- document the conflict in `playbooks/meta/RESEARCH_SNAPSHOT.md`

### Step 5: Convert research into repo changes

Update only what the evidence supports:

- `_base/AGENTS.md`
- `playbooks/personalities/`
- `_base/README.md`
- relevant conventions such as `playbooks/conventions/workbook-convention.md` when doctrine changes
  artifact routing or reusable workflow shape
- `playbooks/meta/RESEARCH_SNAPSHOT.md`

If a finding is interesting but not yet mature, log it under open questions instead of promoting it into default behavior.

### Step 6: Review the resulting template

Run a deliberate review pass:

- is the guidance still concise
- is anything duplicated
- did the template become too vendor-shaped
- are the examples easy to copy into any repo
- did we add complexity without a measurable reason

### Step 7: Record the run

At the end of every refresh:

- update `Last executed`
- refresh `playbooks/meta/RESEARCH_SNAPSHOT.md`
- summarize what changed and why
- list open questions for the next run

## Decision rules for this repo

Promote a finding into the default template only if most of the following are true:

- it improves reliability or quality materially
- it does not depend on one proprietary SDK
- it can be explained simply
- it supports first-principles reasoning or stronger verification
- it helps both single-agent and multi-agent use cases, or has a clearly scoped role

## Deliverables per run

Every completed run should leave behind:

- an updated `playbooks/meta/RESEARCH_SNAPSHOT.md`
- an updated `_base/AGENTS.md`
- updated role cards in `playbooks/personalities/` if behavior changed
- updated conventions or seed docs when behavior changes reusable artifact routing
- refreshed `_base/README.md` examples if the adoption story changed

## Current baseline recommendation

As of 2026-06-18, the template should continue to optimize for:

- simple, composable workflows first
- explicit manager-builder-tester-critic-reviewer passes
- strong evaluation and benchmark skepticism
- durable state for long-running work
- multi-agent specialization only when task structure justifies it
- human-runnable artifacts for substantial or repeatable workflows that humans should be able to
  discover and rerun

## Recent executions

### 2026-07-01

Doctrine refresh for minimal, assumption-aware coding behavior.

- Reviewed the community `multica-ai/andrej-karpathy-skills` guidance and direct local fit through
  parallel subagent research.
- Adapted the portable parts into project-owned base doctrine instead of copying the upstream
  `CLAUDE.md` or adding a person-branded always-on skill.
- Promoted sharper rules for surfacing material assumptions, asking only when inspection cannot
  resolve ambiguity safely, keeping diffs surgical, avoiding speculative flexibility, and cleaning up
  only code made obsolete by the current change.
- Updated `_base/AGENTS.md`, `_base/README.md`, and `playbooks/meta/RESEARCH_SNAPSHOT.md`.

### 2026-06-18

Doctrine refresh for task-native specs and status-aware system mapping.

- Promoted the rule that agents must resolve spec sources and lifecycle status before implementation.
- Added task-local spec/design guidance, optional `Spec refs`, and durable spec statuses.
- Added a seeded system-map index and two workflows: `task-spec-workflow` and `map-system`.
- Updated `_base/AGENTS.md`, task/knowledge conventions, execute/review/closeout workflows,
  `_base/README.md`, `_base/CHANGELOG.md`, and `playbooks/meta/RESEARCH_SNAPSHOT.md`.

### 2026-06-17

Doctrine refresh for human-runnable workflow artifacts.

- Promoted the rule that substantial, repeatable, expensive, or likely-to-be-reused agent-created
  workflows should become documented repo artifacts instead of transcript-only inline snippets.
- Updated `_base/AGENTS.md`, `_base/README.md`, `playbooks/conventions/workbook-convention.md`,
  `_base/workbooks/README.md`, and `playbooks/meta/RESEARCH_SNAPSHOT.md`.
- Kept v1 docs-first with no automated validator because inline-snippet detection would be brittle.
