# Research Snapshot

Current research snapshot for this template.

Reviewed on: 2026-07-01.

## What changed this iteration

The current template now leans harder into:

- explicit multi-pass loops instead of one-shot output
- a default single-agent workflow that emulates manager, builder, tester, critic, and reviewer roles
- evaluation quality as a first-class concern
- durable state and incremental progress for long-running work
- stricter rules for when multi-agent parallelism is worth the coordination cost
- an explicit branch/commit policy based on maintainer operating preference: default branch for
  downstream template-maintenance repos, explicit task branches for working/product repos, and
  coherent checkpoint commits
- task-native spec resolution, with explicit lifecycle status so agents distinguish planned intent
  from implemented system evidence
- a top-level system map that indexes repos, capabilities, flows, and cross-repo boundaries without
  duplicating detailed area docs
- a raw knowledge ingestion lane based on maintainer operating preference: raw source drops stay in a
  staging inbox, while distilled Markdown digests are segregated by area before stable facts are
  promoted into canonical knowledge-base docs
- an autonomy ladder that treats publishing and connector activity as explicit opt-in permission
  ceilings layered on top of existing work-mode and branch rules
- a stricter human-runnable workflow artifact rule for substantial, repeatable, expensive, or
  human-reusable agent-created procedures
- prompt orchestration as a small, task/workbook-backed harness for downstream long tasks, with graph
  runtimes documented as optional upgrades instead of default template dependencies
- sharper coding-discipline defaults: surface material assumptions, ask only when inspection cannot
  resolve meaningful ambiguity safely, keep diffs tied to the request, avoid speculative flexibility,
  and clean up only code made obsolete by the current change

## Current conclusions

### 1. Simple, composable workflows remain the strongest default

Recent provider guidance still converges on the same operational pattern: start with a single agent, add tools and structure, and introduce multi-agent orchestration only when the task clearly benefits from decomposition or parallel reasoning.

Template impact:

- `_base/AGENTS.md` defaults to sequential role emulation first
- multi-agent use is treated as an escalation path, not a starting point

### 2. Critique/refinement loops are still core, but they need external verification

Foundational work like Self-Refine and Reflexion still supports iterative self-feedback. More recent work on process reward models suggests actor-critic style improvement remains an active direction. Operationally, recent engineering guidance reinforces that critique is most useful when tied to tests, transcripts, or explicit evaluators rather than free-form “think harder” prompting.

Template impact:

- every substantial task includes tester and critic passes
- critic output is not trusted by itself; it must drive another concrete verification step

### 3. Evaluation quality is now a bigger differentiator than raw prompt cleverness

Recent evaluation guidance emphasizes clean tasks, reference solutions, balanced problem sets, and grading the produced result rather than the exact path taken. This is reinforced by benchmark-integrity work showing that contaminated or weak benchmarks can mislead teams badly.

Template impact:

- stronger definition-of-done requirements
- more emphasis on executable checks and reference behavior
- explicit skepticism toward benchmark-only optimization

### 4. Long-running agents need durable handoffs and incremental progress

Recent harness work shows agents do better when they start each session by reading progress artifacts, choose one well-scoped task at a time, and leave behind structured state for the next pass. Unstructured “continue until perfect” loops are less reliable without these artifacts.

Template impact:

- `AGENT_PROGRESS.md`, `AGENT_TASKS.json`, and `AGENT_DECISIONS.md` are recommended durable artifacts
- incremental progress is preferred over broad one-shot implementation

### 5. Multi-agent systems help on parallelizable work, but coordination cost is real

Recent production and research writeups show multi-agent systems can unlock more reasoning capacity and specialization, but they also consume many more tokens, introduce coordination failure modes, and fit research-style breadth tasks better than tightly coupled coding tasks.

Template impact:

- explicit ownership and task locks are required for multi-agent work
- the template avoids prescribing multi-agent flows for ordinary repo changes

### 6. Tool ergonomics matter as much as raw model capability

Recent tool-design guidance shows that clearer tool purpose, better descriptions, and evaluation-driven iteration materially improve agent outcomes. More tools are not automatically better.

Template impact:

- agents should prefer a small set of well-defined tools
- repo maintainers should update behavior and artifacts based on observed failure transcripts, not intuition alone

### 7. Benchmarks must be interpreted cautiously

2026 evidence from OpenAI and Anthropic argues that benchmark scores can be distorted by contamination, grader flaws, or infrastructure differences. Small leaderboard gaps are not enough to justify template changes.

Template impact:

- do not change default agent behavior because of a small benchmark delta alone
- require stronger operational evidence before promoting a new pattern

### 8. Loop engineering needs explicit autonomy ceilings

The 2026 loop-engineering discussion is useful because it names the operational shape that this
template already trends toward: discover work, act in small loops, verify, preserve state, and repeat.
The adoption risk is mistaking a loop for permission to publish. The safer interpretation is to keep
local implementation as the default and make remote branch updates, CI repair, draft PR creation, and
connector writes explicit opt-ins.

Template impact:

- added `playbooks/conventions/autonomy-levels.md`
- kept L1 local development as the default for existing repos
- defined L2/L3 as ceilings for branch/CI and draft-PR loops, not as permission to merge or deploy

### 9. Substantial workflows should become human-runnable repo artifacts

Recent tool and skill guidance converges on a practical point: useful procedures should be packaged as
discoverable instructions, scripts, resources, and documented tools instead of being trapped in a
single transcript. Anthropic's Skills guidance explicitly treats scripts/resources as part of reusable
agent capabilities, and its long-running-agent harness work uses setup scripts plus progress artifacts
to make future sessions efficient. OpenAI's agent guidance likewise emphasizes well-documented,
tested, reusable tools as a reliability foundation.

Template impact:

- added a base-contract rule requiring human-runnable artifacts for substantial, repeatable,
  expensive, or likely-to-be-reused workflows
- routed reusable bundles to `workbooks/<workflow-slug>/`, stable operational procedures to
  `docs/resources/<area>/runbooks/`, Python tooling dependencies to `tools/python/`, and
  large/generated/reproducible outputs to `artifacts/README.md`
- strengthened workbook README/script expectations while leaving tiny throwaway inspections inline

### 10. Specs need lifecycle status before agents can safely use them

Recent harness guidance reinforces that specs, sprint contracts, and evaluator criteria help agents
stay on target, but only when the agent knows whether a document is a target or evidence of current
behavior. Durable context guidance also supports keeping orientation docs discoverable and concise
rather than reloading everything into each task. The template now uses task-local specs for executable
planned intent and status-aware resource docs for system reality.

Template impact:

- added optional task `Spec refs`, `Specification`, and `Design`
- added durable spec statuses: `draft`, `accepted`, `partially-implemented`, `implemented`,
  `superseded`
- added `docs/resources/system-map.md` as a status-aware index
- added `task-spec-workflow` and `map-system`

### 11. Prompt orchestration should start as a workbook, not a framework default

Maintainer downstream operating preference points to task-led, workbook-heavy long-running work where
the first reliability need is resumable orientation: task state, current phase, related workbook
commands, artifact/credential checks, verification, critique, and checkpointing. The best default is
therefore a small read-only planning helper plus conventions for prompts, schemas, evals, and traces.
LangGraph-style graph execution remains the right optional upgrade when state transitions,
checkpoint/resume, retries, human interrupts, branching, or parallel lanes become real requirements.

Template impact:

- added `playbooks/conventions/prompt-orchestration.md`
- seeded `_base/workbooks/prompt-orchestration-long-task/`
- extended workbook conventions with optional prompt, schema, eval, and trace folders
- added L0 long-task planning and L1 workbook-backed execution loop recipes
- kept LangChain/LangGraph out of default dependencies

### 12. Coding agents need explicit guardrails against hidden assumptions and drive-by changes

The reviewed Karpathy-inspired community guidance is not strong enough to copy wholesale into the
base contract: it is derivative, has no release tags, and declares MIT without a top-level license
file. Its core failure modes are still real and already align with this template's operating lessons:
agents can silently choose an interpretation, overbuild abstractions, edit adjacent code they do not
fully understand, and proceed without verifiable success criteria. The durable update is to sharpen
the existing project-owned doctrine rather than add a person-branded skill.

Template impact:

- `_base/AGENTS.md` now explicitly requires surfacing material assumptions and ambiguity
- ambiguity should be resolved from local context first; ask only when correctness, safety, scope, or
  user-visible behavior would otherwise be at risk
- implementation diffs should be minimal and surgical, with every changed line traceable to the
  current request, task, or accepted plan
- agents should avoid speculative features, abstractions, extension points, configurability, and
  drive-by cleanup
- agents should clean up only code made obsolete by their own change and report unrelated cleanup
  opportunities instead of taking them silently

## Sources reviewed

| Date | Source | Why it mattered | Repo consequence |
| --- | --- | --- | --- |
| 2026-07-01 | [`multica-ai/andrej-karpathy-skills`](https://github.com/multica-ai/andrej-karpathy-skills) at `2c606141936f1eeef17fa3043a72095b4765b9c2`, plus local subagent audit and plan critique | The maintainer wanted the principles as base repo behavior. The source distilled common coding-agent failure modes but overlapped heavily with existing doctrine and was not license/release-clean enough for verbatim copying | Adapted the portable principles into `_base/AGENTS.md` and `_base/README.md` as project-owned coding discipline; did not vendor the upstream files or add a person-branded always-on skill |
| 2026-06-19 | Maintainer operating preference for downstream task/workbook orchestration | The template needed a practical downstream answer for long tasks without turning every seeded repo into a LangChain/LangGraph app | Added a vendor-neutral prompt orchestration convention and seeded long-task workbook with sanitized synthetic samples |
| 2026-06-18 | [Anthropic, "Harness design for long-running application development"](https://www.anthropic.com/engineering/harness-design-long-running-apps), [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents), [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents), [Equipping agents for the real world with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills), [OpenAI Agent Skills - Codex](https://developers.openai.com/codex/skills), and [OpenAI practical guide to building agents](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/) | Rechecked primary guidance on structured specs/contracts, evaluator criteria, context routing, and reusable skills before changing agent doctrine | Added task-native spec resolution, lifecycle statuses for durable specs, a seeded system map, and two shared skills for task specs and system mapping |
| 2025-10-16 | [Equipping agents for the real world with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) | Shows reusable agent capabilities as organized folders of instructions, scripts, and resources; emphasizes progressive disclosure and scripts as deterministic repeatable tools | Strengthened the workbook convention and base rule so substantial agent-created procedures become documented, runnable repo artifacts |
| 2026-06-17 | [Addy Osmani, "Loop Engineering"](https://addyosmani.com/blog/loop-engineering/) and current Codex manual subagent/custom-agent docs fetched through `openai-docs` | The template needed to absorb loop-engineering terminology without weakening branch, push, PR, or connector boundaries | Added a loop-engineering digest and autonomy-level convention; L1 remains default, L2/L3 require explicit opt-in |
| 2026-05-26 | Maintainer knowledge-base operating preference for this template | The project needs a place to drop raw docs/files and a structured distillation path into durable knowledge | Added `docs/resources/_inbox/`, area-segregated `_digests/`, and `/distill-knowledge` |
| 2026-05-26 | Maintainer operating preference for this template | Branch policy is a project operating constraint rather than a model-behavior research finding | Added default-branch mode for downstream template-maintenance repos and explicit task-branch mode for working/product repos |
| 2026-05-10 | [Claude Code Skills](https://code.claude.com/docs/en/skills), [Codex Skills](https://developers.openai.com/codex/skills), [Agent Skills Specification](https://agentskills.io/specification), [obra/superpowers Codex integration](https://deepwiki.com/obra/superpowers/5.2-codex-integration) | Mapped current dual-runtime conventions: expanded Claude SKILL.md frontmatter (`when_to_use`, `paths`, `allowed-tools`, `model`, `effort`, `hooks`), Codex hook arrival (v0.128, April 2026), Codex MultiAgentV2 (March 2026), `.agents/skills` discovery | Removed Claude-specific tool names from playbooks; left frontmatter expansion and CI lint as future work |
| 2026-02-23 | [Why SWE-bench Verified no longer measures frontier coding capabilities](https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/) | Strong warning on contamination and flawed tests in coding benchmarks | Added explicit benchmark skepticism and stronger evaluation rules |
| 2026-01-09 | [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) | Concrete guidance on solvable tasks, reference solutions, balanced evals, and grader design | Tightened definition of done and testing guidance |
| 2026-01-21 | [Designing AI-resistant technical evaluations](https://www.anthropic.com/engineering/AI-resistant-technical-evaluations) | Reinforces eval integrity as an adversarial problem | Kept evaluation integrity as an explicit update-plan concern |
| 2026-02-05 | [Building a C compiler with a team of parallel Claudes](https://www.anthropic.com/engineering/building-c-compiler) | High-signal lessons on task locks, specialization, and test quality for autonomous teams | Added multi-agent task-lock and ownership rules |
| 2026 | [Quantifying infrastructure noise in agentic coding evals](https://www.anthropic.com/engineering/infrastructure-noise) | Shows infra configuration can move scores by more than leaderboard gaps | Added caution against over-reading small benchmark differences |
| 2025-11-26 | [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) | Best recent source on progress artifacts, setup scripts, and incremental long-running execution | Added recommended durable artifacts, incremental progress rules, and support for preserving reusable setup/workflow steps as repo files |
| 2025-09-29 | [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) | Strong framing for context as a systems-design problem | Strengthened context-discipline rules |
| 2025-09-11 | [Writing effective tools for agents — with agents](https://www.anthropic.com/engineering/writing-tools-for-agents) | Clear evidence that tool ergonomics, tool evals, meaningful context, and choosing the right reusable tool surface matter | Added tool-quality guidance and reinforced docs-first workflow artifacts over transcript-only snippets |
| 2025-06-13 | [How we built our multi-agent research system](https://www.anthropic.com/engineering/built-multi-agent-research-system) | Good evidence on when orchestrator-worker systems pay off and when they are expensive | Multi-agent kept as an escalation path only |
| 2025-03-11 | [New tools for building agents](https://openai.com/index/new-tools-for-building-agents/) | Useful general framing: tools, instructions, models, and reliable agent foundations | Kept template portable and tool-oriented instead of SDK-shaped |
| 2025 | [A practical guide to building AI agents](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/) | Strong general guidance to start simple, define guardrails, scale orchestration only when needed, and keep tools well-documented, tested, reusable, and discoverable | Reinforced single-agent-first design and the new human-runnable artifact rule |
| 2025-02 | [Process Reward Models for LLM Agents: Practical Framework and Directions](https://arxiv.org/abs/2502.10325) | Recent actor-critic direction relevant to the repo’s requested principles | Justified explicit actor-critic language in the template |
| 2023-03-21 | [Reflexion: Language Agents with Verbal Reinforcement Learning](https://arxiv.org/abs/2303.11366) | Foundational support for reflection loops with feedback memory | Preserved critic/refine passes as a core pattern |
| 2023-03-30 | [Self-Refine: Iterative Refinement with Self-Feedback](https://arxiv.org/abs/2303.17651) | Foundational support for iterative self-feedback and revision | Preserved multi-pass refinement as a default behavior |

## Open questions for the next refresh

- Do newer benchmark families like SWE-bench Pro or SWE-Lancer materially change what “good agent behavior” should look like in a portable dev template?
- Is there enough cross-provider evidence yet to recommend a stronger explicit memory protocol beyond simple progress/task/decision files?
