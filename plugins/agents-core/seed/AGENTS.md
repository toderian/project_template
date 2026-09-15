# AGENTS.md

This file is yours (downstream-owned). Shared skills, hooks and subagents come from the
`agents-template` plugins; this file routes to them. Edit it freely — `at init` never overwrites it.

<!-- Claude Code loads this via CLAUDE.md (@AGENTS.md); Codex loads it directly. Keep under 200 lines. -->

## Operating loop

Run every task through these passes, and loop again whenever a pass finds a real problem. A change
you can describe in one sentence skips Frame and Critique — never Test.

- **Frame** — reduce the task to first principles: goal, constraints, invariants, unknowns. Do not
  inherit assumptions from the prompt, stale docs, or existing code without checking them.
- **Build** — make the smallest surgical change that advances the objective.
- **Test** — run the narrowest checks first, then broader regressions; read the real output instead of
  trusting a green summary.
- **Critique** — attack the weakest assumption and look for a simpler design.
- **Review** — check clarity, maintainability, and human adoption fit before calling it done.

## Principles

- **Evidence before action** — read the code, run the checks, verify what materially affects the
  result; treat prior summaries and benchmark claims as hints, not truth.
- **Minimal and surgical diff** — every changed line traces to the current request; no drive-by
  refactors or reformatting; remove the imports, files, and branches your change obsoletes.
- **Evaluation-driven** — define done before large edits, prefer executable checks over confidence,
  and never weaken or delete a test to get green.
- **Context discipline** — load only what the current step needs; write large command output to a file
  and keep head/tail in context; pass references and conclusions, not transcripts.
- **Ratchet failures into rules** — turn a repeated mistake into a durable control (hook, test, skill
  step) at the narrowest layer that catches it, and prune rules that became redundant.
- **Simplicity first** — one agent running the passes in sequence beats orchestration; delegate only
  when the task splits cleanly into independent subproblems.

## Autonomy and git

- Default autonomy is **L1** (local development): inspect, edit, and commit locally; no pushes and no
  destructive or remote operations without an explicit ask. Full ladder: `agents-core:git-discipline`.
- Work on the current or default branch unless the task, this file, or `.config/repos.project.md` says
  otherwise. Do not open a branch merely because commits will happen.
- Plugin hooks block `git push`, `git reset --hard`, `git clean -f`, `git branch -D`, forced staging,
  writes into `.creds/` and other secret paths, and dangerous shell. A block is a guardrail: ask, do not
  route around it. Task-file conventions are reminders only; `at ledger check` is the gate. A role
  subagent that finishes without its `## Status:` block is sent back once to add it.
- Commit after each coherent, reviewable slice — one task phase, one fix, one docs batch. Stage only
  the files that belong to that slice; never sweep in unrelated dirty changes.
- Commit message: a `type: summary` line, then a body with `What changed:` / `Why:` / `Checks:`.

## Routing table

Skill ids below are `plugin:skill`. Invoke them as `/agents-core:tdd` in Claude Code, or
`$agents-core:tdd` in Codex. `agents-core` is always enabled; `agents-tasks`, `agents-extras` and
`agents-personal` are opt-in, so an unknown id means that plugin is not installed here — list the
available skills and pick from that instead of guessing another prefix.

| Your task | Use |
|---|---|
| Implement a tracked task | `agents-core:execute-plan` (+ `agents-tasks:task-ledger` when `docs/tasks_manager/` exists) |
| New feature or bug fix | `agents-core:tdd` |
| Something behaves unexpectedly | `agents-core:diagnose` |
| Plan before code, or scope unclear | `agents-core:planning-workflow`; `agents-tasks:add-task` (spec sections) for a tracked task; `agents-core:spec-workflow` only for multi-session spec artifacts |
| Stress-test a plan or decision with the user | `agents-core:grilling` (+ `agents-extras:domain-modeling` when the glossary matters) |
| Effort too big for one session, way ahead unclear | `agents-tasks:wayfinder` |
| Facts needed from docs, APIs, or the web | a `researcher` dispatch per `agents-core:subagent-protocol` |
| Auth, input handling, crypto, or AI surfaces | `agents-core:security-review-owasp` |
| Branch, commit, or push question | `agents-core:git-discipline` |
| Delegating work | `agents-core:subagent-protocol` (agents: `implementer`, `reviewer`, `researcher`, `plan-critic`, `security-auditor`, `spec-validator`) |
| Pausing or handing off | `agents-core:handoff` |
| Capture an idea, add a task, triage, plan horizons, close out | `agents-tasks:capture-idea`, `agents-tasks:add-task`, `agents-tasks:triage-inbox`, `agents-tasks:roadmap`, `agents-tasks:complete-task` |
| A task plan too big or fuzzy | `agents-tasks:simplify-task` |
| Did a finished task do what its file says | `agents-tasks:verify-task` |
| Durable notes, runbooks, ADRs | `agents-tasks:knowledge-base`, `agents-extras:domain-modeling` for glossary and ADRs |
| A decision only another person can answer | `agents-extras:to-questionnaire` |
| An agent message that did not land | `agents-core:wait-what` |
| Writing a skill, AGENTS.md, or an agent-facing doc | `agents-extras:writing-for-agents` |
| A workflow worth rerunning | `agents-tasks:workbook` |
| Large, generated, or encrypted files | `agents-tasks:artifacts-registry` |
| Work spanning repos | `agents-tasks:cross-repo-feature`, `agents-tasks:cross-repo-pr-review`, `.config/repos.project.md` |
| "Is this over-engineered?" | `agents-core:simplicity-review` |
| Terse replies, fewer output tokens | `caveman:caveman` (`/caveman:caveman` in Claude, `$caveman` in Codex; on by default in Claude, off locally via `.caveman.json`, see conventions) |
| Module shape, interfaces, seams, testability | `agents-core:codebase-design` |
| Setting up this repo, or adopting a template update | `agents-core:setup-project` (after `at update` + restart) |

The skills carry the detail; this file only routes. When a skill covers the task, follow it instead of
improvising a workflow.

## Repository conventions

- `.creds/` — local-only credentials, never committed. Read one only when the task needs it, list
  filenames not contents, never echo or commit a value; name the expected path if one is missing.
- `.prompts/` — reusable prompts that travel with the repo; review for secrets before committing.
  Local-only prompts go to `.no-commit/.prompts/`.
- `.no-commit/` — local scratch: throwaway notes, experiments, raw transcripts. Never committed.
- `.caveman.json` — local, git-ignored switch for the caveman terse-reply mode (`"off"` when output
  wording is the product); `agents-core:setup-project` has the details.
- `.local/` — machine bindings: `repos.map`, runbook values, decrypted artifacts. Never committed.
- `.inbox/` — local drop-zone for files handed to an agent; move anything durable into the repo.
- `tools/python/` — repo-level Python tooling managed with `uv`, not `pip install`; commit
  `pyproject.toml`, `uv.lock`, `.python-version`, never a `.venv/`.
- Large, external, generated, encrypted, or reproducible files — register them in `artifacts/README.md`
  and fetch/verify through that registry instead of walking the tree.

## Definition of done

- The stated objective is satisfied, with the smallest diff that gets there.
- Relevant checks were run and pass, or the gap is called out explicitly.
- Key assumptions were tested or written down.
- The result survived at least one critic pass.
- Task files, docs, and ledgers reflect what is actually true now.

## Project

<!-- The sections below are this repo's own contract. `at doctor` warns while any project slot marker remains; replace each comment with real content. -->

### Summary

<!-- TODO-FILL: what this repo is, who uses it, and the one thing an agent must not break. 2-4 lines. -->

### Commands

<!-- TODO-FILL: the real test / lint / build / run commands and their gotchas, one per line, e.g.
     - test: `make test` (needs a running database; `make test-unit` for the fast subset) -->

### Domain rules and invariants

<!-- TODO-FILL: domain language and rules that must stay true after any change — data that may never
     be rewritten, ordering guarantees, compatibility windows, regulatory constraints. -->

### Repos and areas

<!-- TODO-FILL: the areas of this codebase and their non-obvious constraints; for multi-repo work,
     point at `.config/repos.project.md` and name the sibling repos that matter. -->

### People and coordination

<!-- TODO-FILL: who to coordinate with for which change, review expectations, and anything that needs
     a human decision rather than an agent one. -->
