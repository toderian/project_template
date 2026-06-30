# Base operating contract

> This is `_base/AGENTS.md`: the authoritative, shared base contract for software agents in any project seeded from this template. It is loaded indirectly: each project's root `AGENTS.md` (auto-loaded by Claude Code and Codex) instructs the agent to read this file as part of session start.
>
> **Upstream-owned.** Downstream projects must not edit this file — keep it as inherited so `git fetch template && git merge` updates it cleanly. Project-specific rules go in the downstream-owned `AGENTS.md`.

Portable operating contract for software agents working in any development repository.

At session start, check for available skills before acting. If a skill covers the current task, follow its playbook rather than improvising.

Last aligned with external research: 2026-07-01.

## Objective

Solve the user’s problem with the highest practical quality per unit of time, not with the fastest-looking first draft.

The default posture is:

- think from first principles
- surface material assumptions, ambiguities, and tradeoffs before they become hidden code
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

Interpret `.config/repos.project.md` `Work mode` values as:

- `default-branch`: commit on the configured default branch; if currently elsewhere, ask before
  continuing or switching
- `same-branch`: stay on the current branch; do not create or switch branches
- `task-branch`: use the explicit branch named by the user/task/project; if absent, ask before
  creating or switching
- `read-only`: do not commit; stop if implementation would require writes
- `ask`: ask before edits or branch changes

Autonomy is a separate permission ceiling; see `playbooks/conventions/autonomy-levels.md`. Default to
L1 local development unless repo/task metadata or a direct user request explicitly permits L2/L3.
`Work mode` and branch resolution still decide where work happens, and the strictest rule wins. Never
let autonomy authorize merge, deploy, release, mark-ready-for-review, force-push/history rewrite,
broad connector writes, or secret exposure.

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

0. **Frame**: restate the objective, identify constraints and material assumptions, define done
1. **Understand**: inspect the repo, locate patterns and tests, find the smallest surface
2. **Model**: write down root problem, likely causes, failure modes, verification strategy
3. **Choose workflow**: simple (one agent, sequential roles), medium (extra tester/critic passes), or large (manager coordinates parallel agents with clear ownership)
4. **Build**: implement the minimal step that advances the objective — no speculative refactors or drive-by cleanup
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

## Python tooling environment

For persistent repo-level Python tooling dependencies, use `uv` and keep the environment metadata
under `tools/python/` rather than the repository root. This convention is for tooling helpers, not for
turning every downstream project into a Python package.

- `tools/python/pyproject.toml` declares Python tooling dependencies and should be committed once
  those dependencies exist.
- `tools/python/uv.lock` records the exact resolved dependency state, is committed, and is
  uv-managed; do not hand-edit it.
- `tools/python/.python-version` pins the interpreter for the tooling environment and is committed.
- `tools/python/.venv/` is the local virtual environment and must never be committed. A root `.venv/`
  is also local-only.
- Run managed commands from `tools/python/`, for example `cd tools/python && uv sync` and
  `cd tools/python && uv run <command>`.
- Use `uv add`, `uv remove`, `uv lock`, `uv sync`, and `uv run`; do not use `pip install` directly for
  dependencies that should be represented in committed project state.
- If multiple Python tooling environments are needed, use explicit subfolders under
  `tools/python/<name>/` and document each one in the downstream `AGENTS.md`.

Do not create `tools/python/pyproject.toml`, `tools/python/uv.lock`, or
`tools/python/.python-version` until there are real Python tooling dependencies to represent.

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

For work that produces actionable deliverables (PRDs, triage, planning), use the task convention in `playbooks/conventions/todo-convention.md`; for the golden path, start with `playbooks/conventions/task-system-quickstart.md`. Ideas flow through the **inbox** (`docs/tasks_manager/_inbox/`, `I-NNN`) with `/capture-idea`; captured ideas go through `/triage-inbox`, while clear actionable work can use `/add-task` directly. Tasks live flat in `docs/tasks_manager/_todos/` named `<PREFIX>-NNN-<TYPE>_<desc>.md`; prefixes come from `docs/tasks_manager/_areas.md`, with `T` reserved for default/global/cross-area work, and `TYPE` is `F` feature / `D` debug / `C` chore / `R` research. Do not encode repo slugs in task IDs, filenames, prefixes, or areas; when a downstream project has committed `.config/repos.project.md`, tasks may add an optional `Repos` metadata row with comma-separated repo slugs, and tasks may add optional `Autonomy` metadata (`L0`-`L3`) when intentionally lowering the repo ceiling or requesting a repo-allowed higher loop level. Tasks may add optional `Target date` and `Deadline` metadata (`YYYY-MM-DD` or `N/A`) only when the user explicitly provides task-specific scheduling intent. Tasks may add optional `Spec refs` metadata pointing at `self`, PRDs, `docs/resources/system-map.md`, area docs, feature contracts, or `N/A`; task-local `Specification` and `Design` sections describe planned intent, while durable specs under `docs/resources/` must carry lifecycle status (`draft`, `accepted`, `partially-implemented`, `implemented`, or `superseded`) so agents do not confuse a plan with live system behavior. Reserve new inbox/task IDs with `_base/scripts/reserve-work-item.sh` so parallel agents cannot claim the same number. Each task tracks a brief, optional task-local specification/design, phases, acceptance criteria, related tests or `N/A - <reason>`, follow-ups, an append-only execution log, completion harvest, and completion summary. Before implementing an existing task, run and log a bounded researcher current-state review plus a plan-critic freshness/applicability review; keep these concise for routine tasks and expand only when risk or stale/current facts warrant it. Before code edits, resolve all applicable spec sources and record their lifecycle status in the execution log: `draft` specs are proposals, `accepted` specs are approved targets, `partially-implemented` specs mix live and planned behavior, `implemented` specs are current-state evidence only when backed by code/tests/task history, and `superseded` specs must point to a replacement or be ignored. Reconcile stale, duplicate, out-of-order, or overlapping work before code edits, and ask before merging/cancelling/materially changing scope. `docs/tasks_manager/_roadmap.md` is the roadmap-level Urgent / Now / Next / Later / Someday ordering and may group IDs under dated milestone headings inside those horizons; task files are authoritative for status and detail, while task `Priority` stays metadata. Raw `I-NNN` inbox IDs may appear only in `Someday`; task IDs may appear in any horizon. `docs/areas/_overview.md` and `docs/areas/<slug>.md` are generated area views; `docs/resources/_inbox/` holds raw knowledge drops awaiting `/distill-knowledge`, with related files from one call, teammate handoff, upload bundle, or research bundle grouped in a source batch folder when useful; non-Markdown files there stay ignored by default unless a downstream project intentionally changes that; `docs/resources/_digests/<area-or-bucket>/` holds curated Markdown summaries of raw sources, segregated by area; `docs/resources/_reports/<workflow>/` holds timestamped rerunnable reports, audits, inventories, and migration proposals per `playbooks/conventions/generated-artifacts.md`; `docs/resources/system-map.md` is the status-aware index of participant repos, capability areas, critical flows, and cross-repo boundaries; `docs/resources/<area>/summary.md` holds durable area architecture knowledge; `docs/resources/<area>/sources.md` holds area source history and provenance for teammate inputs, call batches, uploads, durable attachments, and links to related digests/tasks/docs; `docs/resources/<area>/dependency-graph.md` holds cross-repo/package dependency knowledge; `docs/resources/<area>/contracts/<feature-slug>.md` holds concrete cross-repo feature contracts; `docs/resources/<area>/runbooks/<scenario-slug>.md` holds sanitized reusable operational procedures, with real placeholder values kept in ignored `.local/runbooks/<scenario-slug>.local.md`; `docs/resources/<area>/attachments/` holds long-lived committed source documents and binaries, each with nearby Markdown metadata or an index documenting purpose, provenance, area or owner, and update guidance; root `workbooks/` holds reusable workbook bundles, one folder per workbook, with workbook-local scripts/support files and dependencies declared in README `Depends on` paths; `docs/_plans/` holds durable implementation plans; `docs/adr/` holds architecture decision records (`NNNN-slug.md`) per `playbooks/conventions/adr-convention.md`; `docs/resources/CONTEXT.md` is the primary domain glossary; `docs/resources/<area>/components/<component-slug>/CONTEXT.md` holds component context; root `CONTEXT.md` is a pointer/fallback only; `docs/archive/` holds frozen docs/resources. Cross-repo docs should use `<repo-slug>:<repo-relative-path>` source references from `.config/repos.project.md`, never absolute local checkout paths from `.local/repos.map`. Rebuild generated ledgers and area blocks with `_base/scripts/sync-todo-ledgers.sh`; validate read-only with `_base/scripts/sync-todo-ledgers.sh --check`; validate repo registry config with `_base/scripts/check-repos-config.sh` when a project opts into `.config/repos.project.md`. Complete or cancel tasks with `/complete-task`, then archive them in `_todos_archived/`; closeout must reconcile linked spec statuses when the task implements or supersedes them. Claude hooks enforce naming/archive reminders; Codex follows the same playbooks manually. `/tidy-repo` migrates loose work to inbox and loose docs to `docs/resources/` after approval, never silently deleting files.

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

Human-runnable workflow files must have descriptive names, clear entrypoint commands, documented
arguments or config files, expected inputs and outputs, cleanup notes, and no secrets or private local
paths. Capture the method in README or runbook prose, not only in code comments.

Inline snippets remain fine for tiny inspection, quick `rg`/`jq`/JSON parsing, transient environment
checks, or throwaway feasibility experiments. Once the command sequence becomes a procedure, benchmark,
training/evaluation loop, migration helper, report generator, or data-processing workflow someone
would plausibly rerun, turn it into a human-runnable artifact.

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
| `.gitattributes` | **Downstream-owned** | Contains the managed agents-template merge-rule block plus project-specific attributes outside that block. Install or refresh with `_base/scripts/setup-template-merge-rules.sh`. |
| `_base/CHANGELOG.md` | **Upstream-owned** | Base-template changelog. Agents must check this before applying a template merge so they can communicate downstream impact to the user. |
| `_base/SETUP_INSTRUCTIONS.md` | **Upstream-owned** | Numbered setup steps an agent (or human) executes to wire up a fresh project — template remote, runtime installers, downstream-slot replacements, verification. |
| `.config/repos.project.md` (optional) | **Downstream-owned** | Committed project repo registry. Create from `_base/repos.project.example.md` when a project needs stable repo slugs, branch defaults, and work-mode policy. |
| `_base/repos.project.example.md` | **Upstream-owned** | Example repo registry. Do not edit downstream. |
| `_base/repos.map.example` | **Upstream-owned** | Example local checkout map. Copy to `.local/repos.map` and edit locally; do not commit `.local/`. |
| `workbooks/` | **Downstream-owned** | Root workbook bundles. Seeded with an index from `_base/workbooks/README.md`; each workbook owns its own folder and README. |
| `_base/workbooks/` | **Upstream-owned** | Seed root workbook index. Do not edit downstream — root `workbooks/` is the downstream-owned workspace. |
| `tools/python/` | **Downstream-owned** | Optional uv-managed Python tooling metadata. Commit `pyproject.toml`, `uv.lock`, and `.python-version` when dependencies exist; never commit `.venv/`. |
| `PROJECT.md` | **Downstream-owned** | Vision, goals, scope. Copied from `_base/PROJECT.md.template`. Read by the `/align` skill. |
| `_base/PROJECT.md.template` | **Upstream-owned** | Template for `PROJECT.md`. |
| `docs/resources/CONTEXT.md` | **Downstream-owned** | Primary domain glossary (canonical terms, relationships, resolved ambiguities). Seeded from `_base/docs/resources/CONTEXT.md`. Read and updated inline by `grill-with-docs`; consulted by `diagnose`, `zoom-out`, and `refresh-context`. |
| `CONTEXT.md` | **Downstream-owned** | Pointer/fallback to `docs/resources/CONTEXT.md`. Created from `_base/CONTEXT.md.template` when missing. |
| `_base/CONTEXT.md.template` | **Upstream-owned** | Template for the root pointer. |
| `.venv/` | **Local-only** | Local Python virtual environment. Never commit. |
| `tools/python/.venv/` | **Local-only** | Local uv-managed Python tooling environment. Never commit. |
| `.local/runbooks/` | **Local-only** | Machine-local placeholder bindings for sanitized committed runbooks. Never commit. |
| `CHANGELOG.md` (optional) | **Downstream-owned** | Downstream project's own changelog, if they keep one. Never overlaps with `_base/CHANGELOG.md`. |
| `.claude/settings.json` | Mixed | Merge hook entries by hand. |
| `playbooks/`, `skills/`, `.claude/skills/` | Mixed | Accept upstream for skills not customized; keep downstream for forked skills. |

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
