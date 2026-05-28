# Base operating contract

> This is `_base/AGENTS.md`: the authoritative, shared base contract for software agents in any project seeded from this template. It is loaded indirectly: each project's root `AGENTS.md` (auto-loaded by Claude Code and Codex) instructs the agent to read this file as part of session start.
>
> **Upstream-owned.** Downstream projects must not edit this file — keep it as inherited so `git fetch template && git merge` updates it cleanly. Project-specific rules go in the downstream-owned `AGENTS.md`.

Portable operating contract for software agents working in any development repository.

At session start, check for available skills before acting. If a skill covers the current task, follow its playbook rather than improvising.

Last aligned with external research: 2026-05-10.

## Objective

Solve the user’s problem with the highest practical quality per unit of time, not with the fastest-looking first draft.

The default posture is:

- think from first principles
- prefer evidence over guessing
- work in explicit build-test-critic-review loops
- use the smallest workflow that can reliably solve the problem
- keep outputs clear, concise, and directly useful to humans

## Non-negotiable principles

### 1. First-principles reasoning

Before changing anything, reduce the task to:

- goal: what outcome actually matters
- constraints: time, safety, compatibility, product, architecture, policy
- invariants: what must remain true after the change
- unknowns: what must be inspected or tested before acting

Do not inherit accidental assumptions from prompts, stale docs, or existing code without checking them.

### 2. Evidence before action

Inspect the real environment before proposing or implementing changes.

- read the relevant code and docs
- run the existing checks when available
- verify assumptions that materially affect the result
- treat benchmark claims and prior summaries as hints, not truth

### 3. Multi-pass improvement, not one-shot output

Every meaningful task should move through multiple passes:

1. manager pass: frame the task, define done, choose scope
2. builder pass: make the smallest high-value change
3. tester pass: verify behavior, regressions, and edge cases
4. critic pass: attack assumptions, find failure modes, propose a better version
5. reviewer pass: check maintainability, clarity, safety, and user fit

If a pass exposes a real problem, loop again. Do not stop at the first plausible answer.

This is the default actor-critic pattern for this repo:

- actor: the builder produces the next candidate solution
- critic: the tester and critic supply externalized feedback
- manager: decides whether another loop is required

### 4. Simplicity first, orchestration second

Start with a single agent that emulates the above roles sequentially.

Escalate to multi-agent work only when at least one of these is true:

- the task splits cleanly into independent subproblems
- specialized roles materially improve reliability
- the context would otherwise become too large
- the value of extra parallelism justifies the extra cost and coordination risk

If the work is tightly coupled, stay single-agent.

### 5. Evaluation-driven execution

Agents optimize for whatever is measured. Therefore:

- define success before large edits
- prefer executable checks over subjective confidence
- grade outputs and behavior, not just fluent explanations
- do not weaken tests just to get a green result
- when tests are missing, create the lightest credible verification path

### 6. Context discipline

Keep context small and high-signal.

- load only what is needed for the current step
- summarize findings before switching subtasks
- preserve durable state in files when the task is long-running
- pass references and conclusions, not entire transcripts

### 7. Continuous research refresh for core behavior

If changing the repo’s agent doctrine, workflows, role definitions, or evaluation philosophy:

- rerun the process in `playbooks/meta/UPDATE_PLAN.md`
- prefer primary sources
- separate enduring principles from vendor-specific implementation details
- update the dated research snapshot and examples

### 8. Branch, commit, and push discipline

Before code edits, determine the repo mode from the user request, project-specific `AGENTS.md`, task
brief, `repos.project` branch/work policy when present, or current repo convention. `repos.project`
is a default registry; explicit user instructions, task files, or repo-specific `AGENTS.md` override it.

For **downstream template-maintenance repos**:

- work directly on the default branch (`main` or `master`)
- do not create feature branches or subbranches unless the user explicitly asks or the host/CI policy
  requires it
- if the session starts on a non-default branch, ask before continuing or switching

For **working/product repos**:

- work on the explicit task branch named by the user, task file, issue, or project convention at task
  start
- if no task branch is defined, ask for one or ask whether the current branch should be treated as the
  task branch
- do not create nested/subbranches unless the user explicitly asks

In all modes, commit after each coherent, reviewable set of modifications: one task slice, one plan
phase, one bug fix, or one documentation batch. Do not commit every tiny edit, and do not leave a large
completed task as one uncommitted dump.

If asked to commit:

- use a concise conventional summary line with a prefix such as `feat:`, `fix:`, or `chore:`
- always include a commit body, not only a one-line message
- the body should explain what changed and why in a few high-signal lines
- stage only files that belong to the completed slice; never include unrelated dirty changes
- run relevant checks first, or state clearly in the commit/report why they could not be run

If asked to push:

- make sure the local commit message already follows the above format before pushing
- never push unless the user explicitly asks

Default format:

```text
feat: short summary

What changed:
- concise change summary

Why:
- concise reason or user outcome
```

## Standard operating loop

Use this loop by default.

0. **Frame**: restate the objective, identify constraints, define done
1. **Understand**: inspect the repo, locate patterns and tests, find the smallest surface
2. **Model**: write down root problem, likely causes, failure modes, verification strategy
3. **Choose workflow**: simple (one agent, sequential roles), medium (extra tester/critic passes), or large (manager coordinates parallel agents with clear ownership)
4. **Build**: implement the minimal step that advances the objective — no speculative refactors
5. **Test**: run narrowest checks first, then broader regression checks — inspect actual outputs
6. **Critique**: what assumption was weakest? what could still be wrong? is there a simpler design? Then refine.
7. **Review**: ensure the change is understandable, document residual risks, explain what changed and why

## Role definitions

Personalities are role cards an agent adopts during a workflow — they are *not* invocable as slash commands. A single agent moves through them sequentially (or, in multi-agent setups, the manager assigns them to workers).

See `playbooks/personalities/` for detailed role cards including default questions and failure modes:

- `manager.md` — scope, sequencing, exit criteria
- `builder.md` — smallest strong implementation
- `tester.md` — verification, regression detection
- `critic.md` — challenge assumptions, find failure modes
- `reviewer.md` — maintainability, clarity, adoption fitness
- `researcher.md` — research-focused investigation

## Multi-agent rules

If multiple agents are used, the manager must enforce:

- explicit ownership per task or file area
- a shared definition of done
- a task lock or equivalent mechanism for parallel work
- regular integration points
- one final reviewer with authority to reject low-quality merges

Do not create multiple agents to work on the same vague problem statement.

For the full coordination protocol — status vocabulary, dispatch format, two-stage review, escalation rules, and model selection — see `playbooks/skills/productivity/subagent-protocol.md`.

### Available subagents

Subagent definitions for Claude Code live in `.claude/agents/`. Dispatch them when a task benefits from isolated context — an independent perspective the main thread cannot give itself.

| Subagent | Purpose | When to dispatch |
|---|---|---|
| `implementer` | Implement a single task slice from a plan with scope fencing | After a plan is approved and split into slices |
| `reviewer` | Two-stage spec compliance + code quality review | After an implementer reports DONE |
| `plan-critic` | Adversarial plan review using the five-axis rubric in `playbooks/conventions/plan-critique.md` | After a plan is drafted, before any code is written |
| `spec-validator` | Spec-blind behavioral validation — writes tests from acceptance criteria only and reports binary PASS/FAIL | After implementation, as an independent check against the spec |
| `security-auditor` | OWASP + LLM + Agentic AI review using `playbooks/skills/engineering/security-review-owasp.md` | After implementation on any change touching auth, input handling, crypto, or AI surfaces |
| `researcher` | Codebase-first investigation with citation requirements, following `playbooks/personalities/researcher.md` | When the team needs evidence-backed findings before action |

Codex environments vary. If Codex exposes multi-agent tools, use the same dispatch brief and status
vocabulary from `playbooks/skills/productivity/subagent-protocol.md`. If no Codex subagent runtime is
available, `implementer` and `reviewer` remain available as flat installed behavioral skills from
`skills/misc/implementer` and `skills/misc/reviewer`; the other roles (`plan-critic`,
`spec-validator`, `security-auditor`, `researcher`) run on the main thread using the cited personality
and skill/convention.

## Recommended durable artifacts for long-running tasks

When a task spans many sessions, add lightweight artifacts such as:

- `AGENT_PROGRESS.md`: what was done, what failed, what is next
- `AGENT_TASKS.json`: small, checkable tasks with status
- `AGENT_DECISIONS.md`: decisions, assumptions, rejected alternatives

Prefer structured files for task state when possible.
If this template repo is used directly, start from the files in `playbooks/templates/`.

For work that produces actionable deliverables (PRDs, triage, planning), use the task convention in `playbooks/conventions/todo-convention.md`; for the golden path, start with `playbooks/conventions/task-system-quickstart.md`. Ideas flow through the **inbox** (`docs/tasks_manager/_inbox/`, `I-NNN`) with `/capture-idea`; captured ideas go through `/triage-inbox`, while clear actionable work can use `/add-task` directly. Tasks live flat in `docs/tasks_manager/_todos/` named `<PREFIX>-NNN-<TYPE>_<desc>.md`; prefixes come from `docs/tasks_manager/_areas.md`, with `T` reserved for default/global/cross-area work, and `TYPE` is `F` feature / `D` debug / `C` chore / `R` research. Do not encode repo slugs in task IDs, filenames, prefixes, or areas; when a downstream project has committed `repos.project`, tasks may add an optional `Repos` metadata row with comma-separated repo slugs. Reserve new inbox/task IDs with `_base/scripts/reserve-work-item.sh` so parallel agents cannot claim the same number. Each task tracks a brief, phases, acceptance criteria, related tests or `N/A - <reason>`, follow-ups, an append-only execution log, completion harvest, and completion summary. Before implementing an existing task, run and log a bounded researcher current-state review plus a plan-critic freshness/applicability review; keep these concise for routine tasks and expand only when risk or stale/current facts warrant it. Reconcile stale, duplicate, out-of-order, or overlapping work before code edits, and ask before merging/cancelling/materially changing scope. `docs/tasks_manager/_roadmap.md` is the placement-only Now / Next / Later ordering; task files are authoritative for status and detail. `docs/areas/_overview.md` and `docs/areas/<slug>.md` are generated area views; `docs/resources/_inbox/` holds raw knowledge drops awaiting `/distill-knowledge`; `docs/resources/_digests/<area-or-bucket>/` holds curated Markdown summaries of raw sources, segregated by area; `docs/resources/_reports/<workflow>/` holds timestamped rerunnable reports, audits, inventories, and migration proposals per `playbooks/conventions/generated-artifacts.md`; `docs/resources/<area>/summary.md` holds durable area architecture knowledge; `docs/resources/<area>/dependency-graph.md` holds cross-repo/package dependency knowledge; `docs/resources/<area>/contracts/<feature-slug>.md` holds concrete cross-repo feature contracts; `docs/resources/<area>/runbooks/<scenario-slug>.md` holds sanitized reusable operational procedures, with real placeholder values kept in ignored `.local/runbooks/<scenario-slug>.local.md`; `docs/_plans/` holds durable implementation plans; `docs/resources/CONTEXT.md` is the primary domain glossary; `docs/resources/<area>/components/<component-slug>/CONTEXT.md` holds component context; root `CONTEXT.md` is a pointer/fallback only; `docs/archive/` holds frozen docs/resources. Cross-repo docs should use `<repo-slug>:<repo-relative-path>` source references from `repos.project`, never absolute local checkout paths from `.local/repos.map`. Rebuild generated ledgers and area blocks with `_base/scripts/sync-todo-ledgers.sh`; validate read-only with `_base/scripts/sync-todo-ledgers.sh --check`; validate repo registry config with `_base/scripts/check-repos-config.sh` when a project opts into `repos.project`. Complete or cancel tasks with `/complete-task`, then archive them in `_todos_archived/`. Claude hooks enforce naming/archive reminders; Codex follows the same playbooks manually. `/tidy-repo` migrates loose work to inbox and loose docs to `docs/resources/` after approval, never silently deleting files.

## Definition of done

Work is done when:

- the user’s objective is satisfied
- relevant checks pass, or missing checks are explicitly called out
- key assumptions were tested or documented
- the solution survived at least one critic pass
- the final result is concise, clear, and easy for a human to adopt

## Skills and playbooks

This repo includes reusable agent skills shared across Claude Code and Codex.

When docs use slash-style names such as `/tidy-repo`, treat them as skill shorthand. Claude Code may
expose these as slash commands. Codex loads skills into model context; Codex users should invoke them
with natural language or `$skill-name`, not as TUI slash commands.

### How skills work

- `playbooks/` contains the authoritative workflow logic
- `skills/` contains thin Codex wrappers that point to playbooks
- `.claude/skills/` contains thin Claude Code wrappers that point to playbooks

When a skill is invoked, read and follow the referenced playbook. Do not improvise a workflow when a playbook exists for the task.

### When changing a workflow

Update the playbook first. Keep skill wrappers thin — they exist only to route agents to the right playbook with proper metadata.

### Creating new skills

Follow `playbooks/skills/productivity/write-a-skill.md`. Every new skill needs three files: a playbook, a Codex wrapper, and a Claude wrapper.

## Template-remote convention

This repository (`git@github.com:toderian/project_template.git`) is the base template for downstream projects. Every project seeded from it should keep a fetch-only `template` git remote pointing back here, so improvements (new skills, playbook fixes, hook updates) can be pulled in without a manual re-copy.

### File ownership

Downstream projects follow a strict split:

| File | Ownership | Notes |
|------|-----------|-------|
| `AGENTS.md` | **Downstream-owned** | Auto-loaded entrypoint. Each project writes its own project-specific overrides. Loads `_base/AGENTS.md` by instruction. |
| `_base/AGENTS.md` | **Upstream-owned** | This file. Base contract. Do not edit downstream — it flows in cleanly from upstream. |
| `README.md` | **Downstream-owned** | Each project's own README. Links to `_base/README.md`. |
| `_base/README.md` | **Upstream-owned** | Authoritative template documentation. Do not edit downstream. |
| `_base/CHANGELOG.md` | **Upstream-owned** | Base-template changelog. Agents must check this before applying a template merge so they can communicate downstream impact to the user. |
| `_base/SETUP_INSTRUCTIONS.md` | **Upstream-owned** | Numbered setup steps an agent (or human) executes to wire up a fresh project — template remote, runtime installers, downstream-slot replacements, verification. |
| `repos.project` (optional) | **Downstream-owned** | Committed project repo registry. Create from `_base/repos.project.example` when a project needs stable repo slugs, branch defaults, and work-mode policy. |
| `_base/repos.project.example` | **Upstream-owned** | Example repo registry. Do not edit downstream. |
| `_base/repos.map.example` | **Upstream-owned** | Example local checkout map. Copy to `.local/repos.map` and edit locally; do not commit `.local/`. |
| `PROJECT.md` | **Downstream-owned** | Vision, goals, scope. Copied from `_base/PROJECT.md.template`. Read by the `/align` skill. |
| `_base/PROJECT.md.template` | **Upstream-owned** | Template for `PROJECT.md`. |
| `docs/resources/CONTEXT.md` | **Downstream-owned** | Primary domain glossary (canonical terms, relationships, resolved ambiguities). Seeded from `_base/docs/resources/CONTEXT.md`. Read and updated inline by `grill-with-docs`; consulted by `diagnose`, `zoom-out`, and `refresh-context`. |
| `CONTEXT.md` | **Downstream-owned** | Pointer/fallback to `docs/resources/CONTEXT.md`. Created from `_base/CONTEXT.md.template` when missing. |
| `_base/CONTEXT.md.template` | **Upstream-owned** | Template for the root pointer. |
| `.local/runbooks/` | **Local-only** | Machine-local placeholder bindings for sanitized committed runbooks. Never commit. |
| `CHANGELOG.md` (optional) | **Downstream-owned** | Downstream project's own changelog, if they keep one. Never overlaps with `_base/CHANGELOG.md`. |
| `.claude/settings.json` | Mixed | Merge hook entries by hand. |
| `playbooks/`, `skills/`, `.claude/skills/` | Mixed | Accept upstream for skills not customized; keep downstream for forked skills. |

### Agent behavior

Agents working in a downstream project must:

- treat `template` as **fetch-only**; never push to it (the push URL is disabled by convention as `DISABLE`)
- on requests like "update from the template" or "pull template updates", run `git fetch template`, **read `CHANGELOG.md` from the template** (`git diff HEAD..template/master -- CHANGELOG.md`) and surface each new entry's **Downstream impact** line to the user, then show the commit-level diff (`git log --oneline HEAD..template/master`) and let the user choose between `git merge template/master` and selective `git cherry-pick`
- if the `template` remote is missing in a project that clearly originated from this template (it has `AGENTS.md` + `_base/AGENTS.md`, `playbooks/`, `.claude/skills/`), offer to add it:

  ```bash
  git remote add template git@github.com:toderian/project_template.git
  git remote set-url --push template DISABLE
  git fetch template
  ```

- never edit `_base/AGENTS.md` or `_base/README.md` from within a downstream project; suggested base-contract changes belong upstream in the template repo
- when resolving merge conflicts from a template pull, accept upstream for the `_base` files and for skills the downstream has not modified; keep downstream for `AGENTS.md`, `README.md`, and any customized skills/playbooks

See `_base/README.md` → "Staying in sync with the template" for the full workflow.

## Anti-patterns

Avoid these defaults:

- one-shot implementation without verification
- premature multi-agent complexity
- tool spam instead of reasoning
- benchmark chasing without real-task validation
- rewriting tests or requirements to hide failure
- verbose artifacts that make future maintenance harder
- duplicating playbook logic inside skill wrappers
- improvising a workflow when a playbook already covers the task
