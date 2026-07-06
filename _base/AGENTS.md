# Base operating contract

> This is `_base/AGENTS.md`: the authoritative, shared base contract for software agents in any project seeded from this template. It is loaded indirectly: each project's root `AGENTS.md` (auto-loaded by Claude Code and Codex) instructs the agent to read this file as part of session start.
>
> **Upstream-owned.** Downstream projects must not edit this file — keep it as inherited so `git fetch template && git merge` updates it cleanly. Project-specific rules go in the downstream-owned `AGENTS.md`.

Portable operating contract for software agents working in any development repository.

At session start, check for available skills before acting. If a skill covers the current task, follow its playbook rather than improvising.

Last aligned with external research: 2026-07-01.

## Start here (tier 0)

Read this section first. It is the fast path. Load any deeper section below only when the routing table sends you there for the current task.

**Operating loop** — run every task through these passes, and loop again whenever a pass finds a real problem:

- Reduce the task to first principles: goal, constraints, invariants, unknowns. Do not inherit assumptions from prompts or stale code without checking them.
- Make the smallest surgical change that advances the objective — no speculative refactors or drive-by cleanup.
- Test with the narrowest checks first, then broader regressions; inspect real output rather than trusting a green result.
- Critique: attack the weakest assumption and look for a simpler design.
- Review for clarity, maintainability, and human adoption fit before calling it done.

**Autonomy** — default is **L1 local development**; the full ladder and exclusions live in `playbooks/conventions/autonomy-levels.md`.

**Task system** — for actionable deliverables (idea → task → done), follow the golden path in `playbooks/conventions/task-system-quickstart.md`; do not invent your own tracking scheme.

**Ownership** — `_base/**` is upstream-owned: never edit it downstream (it merges cleanly from the `template` remote). Root `AGENTS.md` and `README.md` are downstream-owned project seed; put project-specific rules there.

**Routing table — when your task touches X, read Y before acting:**

| Your task | Load then |
|---|---|
| Implement a tracked task | `playbooks/conventions/todo-convention.md` + `task-system-quickstart.md` |
| Triage the inbox | `playbooks/conventions/inbox-convention.md` |
| Roadmap horizons / prioritization | `playbooks/conventions/todo-convention.md` §Roadmap |
| Autonomy, branch, or commit questions | `playbooks/conventions/autonomy-levels.md` + §"Branch, commit, and push discipline" below |
| Security-sensitive change | `security-review-owasp` skill |
| Multi-repo / cross-repo work | `_base/scripts/check-repos-config.sh` + `.config/repos.project.md` (downstream, if present) |
| Knowledge base / durable notes | `playbooks/conventions/knowledge-base-quickstart.md` |
| Runbooks | `playbooks/conventions/runbook-convention.md` |
| Workbooks | `playbooks/conventions/workbook-convention.md` |
| ADRs | `playbooks/conventions/adr-convention.md` |
| Generated reports / timestamped outputs | `playbooks/conventions/generated-artifacts.md` |
| Connectors / MCP tools | `playbooks/conventions/connectors-and-mcp.md` |
| Automating a recurring agent loop | `playbooks/conventions/agent-loop-recipes.md` |
| Prompt / multi-agent orchestration | `playbooks/conventions/prompt-orchestration.md` |
| Preserving a repeatable workflow (don't leave it in the transcript) | §"Human-runnable workflow artifacts" below |

— End of tier 0. Everything below is reference material; load a section only when the routing table above points you to it for the current task. —

## Non-negotiable principles

### 1. First-principles reasoning

Before changing anything, reduce the task to:

- goal: what outcome actually matters
- constraints: time, safety, compatibility, product, architecture, policy
- invariants: what must remain true after the change
- unknowns: what must be inspected or tested before acting

Do not inherit accidental assumptions from prompts, stale docs, or existing code without checking them.
When ambiguity materially affects correctness, safety, scope, or user-visible behavior, first try to
resolve it from local context. Ask the user only when inspection cannot resolve it safely. When the
ambiguity is low-risk, proceed with the smallest reversible assumption and state it clearly.

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

If a pass exposes a real problem, loop again. Do not stop at the first plausible answer. This is the
repo's default actor-critic pattern: the builder produces candidates, the tester and critic supply
externalized feedback, and the manager decides whether another loop is required.

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
- for large command or tool output, keep only the head and tail in context and write the full output
  to a scratch file, then read back the specific slice you need on demand (the optional `context-mode`
  plugin in `_base/README.md` automates this)

### 7. Minimal and surgical implementation

For implementation work, keep the diff tied to the actual objective.

- every changed line should trace back to the current request, task, or accepted plan
- prefer the smallest code change that solves the present problem
- do not add speculative features, abstractions, extension points, configurability, or future-proofing
- match existing style and local patterns, even when a different style would be reasonable elsewhere
- do not reformat, rename, refactor, or "clean up" adjacent code as a side effect
- remove imports, variables, files, and branches made obsolete by your own change
- mention pre-existing dead code or unrelated cleanup opportunities instead of changing them unless asked
- add defensive handling at real external, user-input, security, concurrency, or persistence boundaries;
  do not build scaffolding for scenarios that are only "impossible" because of an unverified assumption

### 8. Continuous research refresh for core behavior

If changing the repo’s agent doctrine, workflows, role definitions, or evaluation philosophy:

- rerun the process in `playbooks/meta/UPDATE_PLAN.md`
- prefer primary sources
- separate enduring principles from vendor-specific implementation details
- update the dated research snapshot and examples

### 9. Branch, commit, and push discipline

Before code edits, determine the repo mode from the user request, project-specific `AGENTS.md`, task
brief, `.config/repos.project.md` branch/work policy when present, or current repo convention.
`.config/repos.project.md` is a default registry; explicit user instructions, task files, or
repo-specific `AGENTS.md` override it.

When executing an approved task or plan, read and validate `.config/repos.project.md` before deciding
branch behavior. If no registry is present in a template-inherited downstream repo, default to
the repo's configured default branch (`main` or `master` in most repos); if already on a non-default
branch, ask before continuing. Do not create a feature/task branch merely because commits will be made.

For **downstream template-maintenance repos**:

- work directly on the default branch (`main` or `master`)
- do not create feature branches or subbranches unless the user explicitly asks or the host/CI policy
  requires it
- if the session starts on a non-default branch, ask before continuing or switching

For **working/product repos**:

- work on the current/default branch unless a user instruction, task file, issue, repo-specific
  `AGENTS.md`, or `.config/repos.project.md` row explicitly says `task-branch`
- when `task-branch` mode applies and no task branch is defined, ask for one or ask whether the
  current branch should be treated as the task branch
- do not create nested/subbranches unless the user explicitly asks

The `.config/repos.project.md` `Work mode` values (`default-branch` / `same-branch` / `task-branch` /
`read-only` / `ask`) are defined in `_base/repos.project.example.md`; the separate autonomy ceiling
(default **L1**) lives in `playbooks/conventions/autonomy-levels.md`. Work mode and branch resolution
decide *where* work happens; autonomy decides *how far* it may go; the strictest rule wins.

In all modes, commit after each coherent, reviewable set of modifications: one task slice, one plan
phase, one bug fix, or one documentation batch. Do not commit every tiny edit, and do not leave a large
completed task as one uncommitted dump.

For downstream repos, once an execute-plan task is fully implemented, validated, and reviewed, the
task's own phase/review commits may be squashed into a single final task commit. Route that cleanup
through `squash-workspace-commits`: audit first, squash only safely identifiable task commits, preserve
the important commit-message details, and never rewrite pushed/shared history without explicit user
approval.

Task progress files are part of the work. When implementing a tracked task, update phase checkboxes,
`Updated`, `Last executed`, and the append-only execution log as work progresses. If implementation is
complete but the task still lives in `_todos/`, run the task closeout workflow rather than leaving the
backlog stale.

If asked to commit:

- use a concise conventional summary line with a prefix such as `feat:`, `fix:`, or `chore:`
- always include a commit body, not only a one-line message
- the body should explain what changed and why in a few high-signal lines
- stage only files that belong to the completed slice; never include unrelated dirty changes
- run relevant checks first, or state clearly in the commit/report why they could not be run

If asked to push:

- make sure the local commit message already follows the above format before pushing
- never push unless the user explicitly asks and effective autonomy permits L2 or L3 for the resolved
  branch

### 10. Ratchet failures into durable rules

Treat a repeated agent mistake as a permanent signal, not a one-off. Every standing rule, guardrail,
and anti-pattern should trace back to a real past failure or a hard external constraint.

- when a class of mistake recurs, convert it into a durable control: a playbook step, a hook, a
  test/pre-commit check, an anti-pattern entry, or a reviewer-subagent blocker — not a one-time fix
- put each new rule at the narrowest layer that catches it (a hook or check beats prose the agent must
  remember; a targeted rule beats a broad one that competes for attention)
- prune the other way too: remove rules that models or tooling have made redundant, so the contract
  stays high-signal
- doctrine-level changes still follow principle 8 (rerun `playbooks/meta/UPDATE_PLAN.md`, prefer
  primary sources)

## Role definitions

Personalities are role cards an agent adopts during a workflow — they are *not* invocable as slash commands. A single agent moves through them sequentially (or, in multi-agent setups, the manager assigns them to workers).

See `playbooks/personalities/` for detailed role cards including default questions and failure modes:

- `manager.md` — scope, sequencing, exit criteria
- `builder.md` — smallest strong implementation
- `tester.md` — verification, regression detection
- `critic.md` — challenge assumptions, find failure modes
- `reviewer.md` — maintainability, clarity, adoption fitness
- `researcher.md` — research-focused investigation

## Python tooling environment

For persistent repo-level Python tooling, use `uv` (not `pip install`) and keep the environment under
`tools/python/`, not the repo root — this is for tooling helpers, not for turning the project into a
Python package. Commit `pyproject.toml`, `uv.lock`, and `.python-version`, but only once real
dependencies exist; never commit any `.venv/` (`tools/python/.venv/` or a root one). Run managed
commands from `tools/python/` (`cd tools/python && uv sync`, `uv run <command>`, `uv add`/`remove`/
`lock`). For multiple tooling environments, use `tools/python/<name>/` subfolders and document each in
the downstream `AGENTS.md`.

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

Codex environments vary: if Codex exposes multi-agent tools, use the same dispatch brief and status
vocabulary; otherwise `implementer` and `reviewer` run as flat skills (`skills/misc/*`) and the other
roles run on the main thread using their cited personality/skill.

## Recommended durable artifacts for long-running tasks

When a task spans many sessions, add lightweight artifacts such as:

- `AGENT_PROGRESS.md`: what was done, what failed, what is next
- `AGENT_TASKS.json`: small, checkable tasks with status
- `AGENT_DECISIONS.md`: decisions, assumptions, rejected alternatives

Prefer structured files for task state when possible.
If this template repo is used directly, start from the files in `playbooks/templates/`.

For actionable deliverables (PRDs, triage, planning), use the task system rather than an ad-hoc
scheme. Each concern has a single canonical owner reachable from the tier-0 routing table — task
files, inbox, and roadmap (`todo-convention.md`, `inbox-convention.md`), durable knowledge
(`knowledge-base-quickstart.md`), reports (`generated-artifacts.md`), ADRs (`adr-convention.md`), and
workbooks (`workbook-convention.md`). Durable plans live in `docs/_plans/`; frozen docs in
`docs/archive/`. Do not restate those conventions here.

Do not encode repo slugs into task IDs, filenames, prefixes, or areas. Claude hooks enforce
naming/archive reminders and the `.claude/hooks/block-dangerous-*.sh` command guards are accident
guardrails (not a security boundary; require `jq`; fail closed rather than no-op); Codex follows the
same playbooks manually. When authoring or extending a hook, keep it silent on success (`exit 0`, no
output) and verbose only when it blocks (`exit 2` with actionable stderr), and anchor match patterns
narrowly — a false positive costs more attention than it saves. `/tidy-repo` migrates loose work to
the inbox and loose docs to `docs/resources/` after approval, never silently deleting files.

## Human-runnable workflow artifacts

Do not leave substantial workflow logic only in the chat transcript or in one-off inline shell/Python
snippets. If a workflow is substantial, repeatable, expensive to recreate, or likely to be useful to
the human later, preserve it as documented repo files before considering the task done.

Use these routing rules:

- `workbooks/<workflow-slug>/`: reusable workflow bundles with scripts, configs, sample inputs,
  support files, methodology notes, and documented outputs.
- `docs/resources/<area>/runbooks/`: stable operational procedures such as setup, SSH, service
  inspection, deployment checks, incident/debugging procedures, and other sanitized commands humans
  or agents will run again.
- `tools/python/`: repo-level Python tooling dependencies managed with `uv`; workbook or runbook
  scripts may depend on this environment when the dependency should be represented in committed
  project state.
- `artifacts/README.md`: large, external, generated, encrypted, or reproducible artifacts that must be
  discoverable by slug, backend, path or pattern, fetch command, verification command, encryption
  status, and update notes.

Such files need descriptive names, clear entrypoint commands, documented arguments/inputs/outputs,
cleanup notes, no secrets or private local paths, and the method captured in README/runbook prose (not
only code comments). Inline snippets stay fine for tiny inspection or throwaway experiments; once a
command sequence becomes a procedure someone would rerun (benchmark, migration helper, report
generator, data-processing loop), turn it into an artifact.

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
| `AGENTS.md` | **Downstream-owned** | Auto-loaded entrypoint; project-specific overrides. Loads `_base/AGENTS.md` by instruction. |
| `README.md` | **Downstream-owned** | Project's own README; links to `_base/README.md`. |
| `.gitattributes` | **Downstream-owned** | Holds the managed template merge-rule block; install/refresh with `_base/scripts/setup-template-merge-rules.sh`. |
| Everything under `_base/` | **Upstream-owned** | Base contract, README, changelog, setup instructions, examples, and `*.template` seeds. Never edit downstream; accept upstream on merge conflicts. |
| `.claude/settings.json` | Mixed | Merge hook entries by hand. |
| `playbooks/`, `skills/`, `.claude/skills/` | Mixed | Accept upstream for skills not customized; keep downstream for forked skills. |

The full per-file inventory (downstream-owned `PROJECT.md`, `CONTEXT.md`, `workbooks/`, `tools/python/`;
local-only `.venv/`, `.local/`; the optional downstream `CHANGELOG.md`; etc.) lives in
`_base/README.md` → "Staying in sync with the template".

### Agent behavior

Agents working in a downstream project must:

- treat `template` as **fetch-only**; never push to it (the push URL is disabled by convention as `DISABLE`)
- before template merges, run `_base/scripts/setup-template-merge-rules.sh --check`; if it fails, run
  `_base/scripts/setup-template-merge-rules.sh`, commit `.gitattributes` if it changed, then retry the
  merge
- on requests like "update from the template" or "pull template updates", run `git fetch template`, **read `_base/CHANGELOG.md` from the template** (`git diff HEAD..template/master -- _base/CHANGELOG.md`) and surface each new entry's **Downstream impact** line to the user, then show the commit-level diff (`git log --oneline HEAD..template/master`) and let the user choose between `git merge template/master` and selective `git cherry-pick`
- when base updates introduce or change downstream-owned formats, seeded docs, task metadata,
  project-slot files, or local setup conventions, ask whether the user wants to migrate the downstream
  repo to the updated base format; do not silently rewrite downstream-owned files as part of the
  template merge
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
