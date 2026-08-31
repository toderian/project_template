# AGENTS.md

This file is yours (downstream-owned). Shared skills, hooks and subagents come from the
`agents-template` plugins; this file routes to them. Edit it freely — `at init` never overwrites it.

<!-- Claude Code loads this via CLAUDE.md (@AGENTS.md); Codex loads it directly. Keep under 200 lines. -->

## Operating loop

Run every task through these passes, and loop again whenever a pass finds a real problem.

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
  destructive or remote operations without an explicit ask. Full ladder: `git-discipline`.
- Work on the current or default branch unless the task, this file, or `.config/repos.project.md` says
  otherwise. Do not open a branch merely because commits will happen.
- Hooks shipped with the plugins block `git push`, `git reset --hard`, `git clean -f`,
  `git branch -D`, forced staging, writes into `.creds/` and other secret paths, and dangerous shell.
  A block is a guardrail: ask, do not route around it.
- Commit after each coherent, reviewable slice — one task phase, one fix, one docs batch. Stage only
  the files that belong to that slice; never sweep in unrelated dirty changes.
- Commit message: a `type: summary` line, then a body with `What changed:` / `Why:` / `Checks:`.

## Routing table

Skill ids below are `plugin:skill`. Invoke them as `/agents-core:tdd` in Claude Code, or `$tdd`
(prefix dropped) in Codex. `agents-core` is always enabled; `agents-tasks`, `agents-extras` and
`agents-personal` are opt-in, so an unknown id means that plugin is not installed here — list the
available skills and pick from that instead of guessing another prefix.

| Your task | Use |
|---|---|
| Implement a tracked task | `agents-core:execute-plan` (+ `agents-tasks:task-ledger` when `docs/tasks_manager/` exists) |
| New feature or bug fix | `agents-core:tdd` |
| Something behaves unexpectedly | `agents-core:diagnose` |
| Scope or requirements unclear | `agents-core:spec-workflow`, or `agents-core:task-spec-workflow` for a tracked task |
| Stress-test a plan or decision with the user | `/agents-core:grill-me`, or `/agents-extras:grill-with-docs` when the glossary matters |
| Effort too big for one session, way ahead unclear | `agents-tasks:wayfinder` |
| Before writing a plan | `agents-core:planning-workflow` |
| Facts needed from docs, APIs, or the web | `agents-core:research` |
| Auth, input handling, crypto, or AI surfaces | `agents-core:security-review-owasp` |
| Branch, commit, or push question | `agents-core:git-discipline` |
| Delegating work | `agents-core:subagent-protocol` (agents: `implementer`, `reviewer`, `researcher`, `plan-critic`, `security-auditor`, `spec-validator`) |
| Pausing or handing off | `agents-core:handoff` |
| Capture an idea, add a task, triage, plan horizons, close out | `agents-tasks:capture-idea`, `agents-tasks:add-task`, `agents-tasks:triage-inbox`, `agents-tasks:roadmap`, `agents-tasks:complete-task` |
| Durable notes, runbooks, ADRs | `agents-tasks:knowledge-base`, `agents-extras:domain-modeling` for glossary and ADRs |
| A decision only another person can answer | `agents-extras:to-questionnaire` |
| An agent message that did not land | `/agents-core:wait-what` |
| Writing a skill, AGENTS.md, or an agent-facing doc | `agents-extras:writing-for-agents` |
| A workflow worth rerunning | `agents-tasks:workbook` |
| Large, generated, or encrypted files | `agents-tasks:artifacts-registry` |
| Work spanning repos | `agents-tasks:cross-repo-feature`, `agents-tasks:cross-repo-pr-review`, `.config/repos.project.md` |
| "Is this over-engineered?" | `agents-core:simplicity-review` |
| Module shape, interfaces, seams, testability | `agents-core:codebase-design` |
| Setting up this repo, or adopting a template update | `agents-core:setup-project` (after `at update` + restart) |

The skills carry the detail; this file only routes. When a skill covers the task, follow it instead of
improvising a workflow.

## Repository conventions

- `.creds/` — local-only credentials, never committed. Read a file only when the task genuinely needs
  it, and list filenames rather than contents. Never echo, paste, summarise, or commit a credential
  value; if one is missing, name the expected `.creds/<filename>` path instead of inventing it.
- `.prompts/` — reusable prompts that should travel with the repo. Committable by design, but review
  each one for secrets and private context before committing; local-only prompts go to
  `.no-commit/.prompts/`.
- `.no-commit/` — local scratch: throwaway notes, experiments, raw transcripts. Never committed.
- `.local/` — machine bindings: `repos.map`, runbook values, decrypted artifacts. Never committed.
- `.inbox/` — local drop-zone for files handed to an agent. Treat it as staging; move anything durable
  into the repo (or `docs/resources/_inbox/`) before relying on it.
- `tools/python/` — repo-level Python tooling managed with `uv`, not `pip install`. Commit
  `pyproject.toml`, `uv.lock`, and `.python-version` once real dependencies exist; never commit a
  `.venv/`. Run managed commands from `tools/python/`.
- Large, external, generated, encrypted, or reproducible files — register them in `artifacts/README.md`
  and fetch/verify through that registry instead of walking the tree.

## Definition of done

- The stated objective is satisfied, with the smallest diff that gets there.
- Relevant checks were run and pass, or the gap is called out explicitly.
- Key assumptions were tested or written down.
- The result survived at least one critic pass.
- Task files, docs, and ledgers reflect what is actually true now.

## Anti-patterns

- One-shot implementation with no verification of real output.
- Speculative abstraction, configuration, or future-proofing nobody asked for.
- Rewriting, skipping, or loosening tests to hide a failure.
- Improvising a workflow that an existing skill already covers.
- Dumping large tool output into context instead of a file.

## Project

<!-- The sections below are this repo's own contract. `at doctor` warns while any project slot marker remains; replace each comment with real content. -->

### Summary

<!-- TODO-FILL: what this repo is, who uses it, and the one thing an agent must not break. 2-4 lines. -->

### Commands

<!-- TODO-FILL: the real test / lint / build / run commands and their gotchas, one per line, e.g.
     - test: `make test` (needs a running database; `make test-unit` for the fast subset)
     - lint: `make lint`
-->

### Domain rules and invariants

<!-- TODO-FILL: domain language and rules that must stay true after any change — data that may never
     be rewritten, ordering guarantees, compatibility windows, regulatory constraints. -->

### Repos and areas

<!-- TODO-FILL: the areas of this codebase and their non-obvious constraints; for multi-repo work,
     point at `.config/repos.project.md` and name the sibling repos that matter. -->

### People and coordination

<!-- TODO-FILL: who to coordinate with for which change, review expectations, and anything that needs
     a human decision rather than an agent one. -->
