---
name: spec-workflow
description: "Spec-driven plan-build-review-fix loop for a non-trivial item, producing specs/<slug>/ artifacts. Use when the user asks to \"spec it out\" / \"spec workflow\" / \"spec-driven\", or needs plan+build+review too large for the default loop; not trivial edits or spikes."
metadata:
  source: playbooks/skills/engineering/spec-workflow.md
  pack: core
---

# Spec Workflow

## Purpose

A heavyweight plan → build → review → fix loop for a single piece of engineering work. Produces four durable artifacts under `specs/<slug>/` (`spec.md`, `design.md`, `tasks.md`, `review.md`) and dispatches parallel implementers via the existing `agents-core:subagent-protocol`. Runtime-agnostic: same playbook and artifacts on Claude Code and Codex (dispatch mechanics differ — see Phase 2).

## When to use

- Non-obvious feature where the plan itself is the hard part.
- Work that splits cleanly into ≥3 parallelizable task groups.
- Cross-cutting change worth a written spec + an explicit reviewer pass.
- Resumable multi-session work where artifacts must survive context resets.

This is the heavyweight cousin of `agents-tasks:prd-to-plan`. Choose it when parallel subagent dispatch is already on the table.

## When NOT to use

- Single-file edits, typos, trivial bug fixes.
- Exploratory spikes where you don't yet know what "done" looks like.
- Anything one builder pass + one critic pass can cover.

Forward those to the default operating loop in `AGENTS.md` § "Standard operating loop". From the `agents-core:subagent-protocol` skill § "When to dispatch subagents": *if work is tightly coupled, stay single-agent*. The same logic gates this skill.

## Composition with the PRD chain

Input can be any of:

- A PRD GitHub issue (`gh issue view N`).
- A local PRD file.
- An existing `docs/_plans/<feature>.md` produced by `agents-tasks:prd-to-plan`.
- A rough intent the user types directly.

This skill does **not** replace the PRD chain (`agents-extras:write-a-prd`, `agents-tasks:prd-to-plan`, `agents-extras:prd-to-issues`, `agents-tasks:prd-to-todos`). `spec.md` is per-work-item engineering intent, not a product PRD. If a PRD already exists, summarize it into `spec.md`; if not, start from intent.

## Workflow (the loop)

```
intent / PRD ──► Plan ──► Build ──► Review ─┬─► STOP (review PASS, no concerns)
                  ▲                          │
                  └────── append fix tasks ──┘   (review FAIL or concerns)
```

After 3 review cycles, **escalate to the user** instead of looping a 4th time. Repeated failure is a signal to reframe the work, not loop harder.

The four phases below stay consistent with `AGENTS.md` § "Standard operating loop" (frame → understand → model → choose workflow → build → test → critique → review). spec-workflow is a structured instantiation of that loop, not a replacement.

## Artifact location & layout

All four files live at `specs/<slug>/` from the project root.

- `<slug>` is kebab-case, derived from the spec title, confirmed with the user before any file is written.
- If `specs/` does not exist, create it.
- This skill must never write outside `specs/<slug>/`.

## File schemas

Inlined here so they are visible at read time. Treat each block as a canonical template — populate sections, do not invent new top-level headings.

### `spec.md`

```markdown
# <Spec title>

## Source
<PRD link / issue / "rough intent">, captured <date>

## Problem
One paragraph. What is broken / missing. Whose pain.

## Goal
One paragraph. The outcome that proves the problem is solved.

## Success criteria
- [ ] Testable condition 1
- [ ] Testable condition 2

## Non-goals
Things explicitly out of scope so reviewers don't flag them as gaps.

## Constraints
Time, compatibility, performance, security, policy — anything that
narrows the solution space.

## Open questions
Things the agent flagged for the user. Resolve before moving to design.md.
```

### `design.md`

```markdown
# <Spec title> — Design

## Approach summary
2–4 sentences naming the chosen approach.

## Architecture decisions
For each major decision:
- Decision: <what>
- Why: <reasoning, grounded in existing patterns>
- Alternatives considered: <one-line each, why rejected>
- Risks: <what could go wrong>

## Components touched
File-by-file or module-by-module map of changes.

## Data / API / interface changes
Schema diffs, endpoint signatures, public API changes. Empty section if none.

## Testing strategy
Which layer (unit / integration / e2e) covers which success criterion.

## Rollout & reversibility
How to ship; how to roll back.
```

### `tasks.md`

```markdown
# <Spec title> — Tasks

## Parallel groups
Tasks within a group are file-disjoint and can be dispatched in parallel.
Groups are sequenced.

### Group 1
- [ ] T1.1 <one-line task> — scope: <file globs> — verifies: <criterion ref>
- [ ] T1.2 <one-line task> — scope: <file globs> — verifies: <criterion ref>

### Group 2
- [ ] T2.1 ...

## Fix iterations
(Appended after each failed review pass.)

### Fix iteration 1 — <date>
- [ ] F1.1 <one-line task> — addresses: review.md § "Iteration 1" finding 3
```

Each task line gets a status annotation once dispatched. Glyphs and status text reuse the `agents-core:subagent-protocol` skill § "Status vocabulary":

| Glyph | Status |
|-------|--------|
| `[ ]` | not started |
| `[x]` | DONE |
| `[~]` | DONE_WITH_CONCERNS |
| `[!]` | BLOCKED |
| `[?]` | NEEDS_CONTEXT |

Example:

```markdown
- [~] T1.3 Update profile UI — scope: web/profile/** — verifies: #4 — DONE_WITH_CONCERNS: copy not reviewed
- [!] T1.4 Add audit log — scope: services/audit/** — verifies: #5 — BLOCKED: needs schema decision
```

No parallel `AGENT_TASKS.json` for this skill — `tasks.md` is the single state file under `specs/<slug>/`. The generic assets/AGENT_TASKS.template.json remains available for non-spec-workflow long-running tasks.

### `review.md`

```markdown
# <Spec title> — Review log

## Iteration 1 — <date>
**Dispatched against:** commit range <base>..<head>
**Reviewer status:** DONE | DONE_WITH_CONCERNS
**Spec compliance:** PASS | FAIL

### Failed criteria
- <criterion ref> — <gap>

### Quality issues
- <one-line concern>

### Verdict
<one line>

## Iteration 2 — <date>
...
```

`review.md` is **append-only**. Each iteration adds a new section; nothing is rewritten.

## Phase 1 — Plan

1. Resolve input source (issue / file / intent). Use `gh issue view N` only if input is an issue number.
2. Pick `<slug>`; confirm with the user; create `specs/<slug>/` if missing.
3. Draft `spec.md` from input. Stop and resolve any "Open questions" with the user before
   proceeding — run the `agents-core:grilling` skill when there is more than one of them.
4. Explore the codebase to ground design choices using Read / Grep / Glob — **single-agent**, no subagent dispatch yet.
5. Draft `design.md`.
6. Draft `tasks.md` with parallel groups marked.
7. Show the user a one-screen summary of `spec.md` + groups in `tasks.md`. Get a single approval. Do not over-quiz.

## Phase 2 — Build (dispatch mechanics)

Group tasks into parallel-safe sets (no shared files, no ordering dependency). For each group:

1. For each task, construct a dispatch brief per the `agents-core:subagent-protocol` skill § "Dispatch briefing format". Required fields:
   - Task description (from the `tasks.md` line).
   - Acceptance criteria (lifted from the task + linked `spec.md` criterion).
   - Scope fence (file globs from the task).
   - Personality: the `builder` personality (subagent-protocol skill, references/personalities/builder.md).
   - Context files: `specs/<slug>/spec.md`, `specs/<slug>/design.md`, plus task-relevant existing source files.
   - Model hint per the `agents-core:subagent-protocol` skill § "Model selection".
2. Dispatch the group. **Runtime parity, not runtime identity:**
   - **Claude Code:** use the `Task` tool with `subagent_type: implementer` to dispatch all tasks in the group in parallel.
   - **Codex:** use Codex multi-agent tools when available. If unavailable, invoke the behavioral
     `/implementer` skill per task in a recommended order; the grouping still encodes "safe to
     interleave" intent.
   - Both runtimes use the same brief shape and the same status vocabulary.
3. Collect each subagent's structured report. Annotate the corresponding `tasks.md` line with its returned status (glyph + status text per § "File schemas").
4. If any task returns `BLOCKED` or `NEEDS_CONTEXT`, follow the `agents-core:subagent-protocol` skill § "Escalation rules". Never re-dispatch with an identical prompt.
5. Repeat for the next group until every task in every group is `DONE` or `DONE_WITH_CONCERNS`.

## Phase 3 — Review

1. Determine the diff range: last passing baseline → HEAD.
2. Build a reviewer brief:
   - Context files: `specs/<slug>/spec.md`, `specs/<slug>/tasks.md`, plus the diff range.
   - Personalities: the `reviewer` personality (subagent-protocol skill, references/personalities/reviewer.md) + the `critic` personality (subagent-protocol skill, references/personalities/critic.md).
   - Acceptance: two-stage review per the `agents-core:subagent-protocol` skill § "Two-stage review" — Stage 1 spec compliance (PASS/FAIL), Stage 2 code quality.
3. Dispatch one reviewer:
   - **Claude Code:** `Task` tool with `subagent_type: reviewer`.
   - **Codex:** invoke the `/reviewer` skill.
4. Append the reviewer's report as a new `## Iteration N — <date>` section to `review.md`. Do not overwrite earlier iterations.

## Phase 4 — Terminate or loop

Parse the reviewer's status. Termination criteria (any one stops the loop):

- Status `DONE` and Spec compliance `PASS` and no quality issues → done.
- Status `DONE_WITH_CONCERNS` and the user explicitly accepts the residual concerns.
- 3 review cycles elapsed → escalate to the user; do not loop a 4th time.

Otherwise: append a `## Fix iteration N` section to `tasks.md` with one new task per failed criterion / blocking quality issue. Then jump back to Phase 2.

When terminating, append a final `### Verdict` line to the last iteration in `review.md` and stop.

## Recursive mitigation

Dispatched implementer and reviewer subagents must **not** load `AGENTS.md` or scan the skills directory — per `.claude/agents/implementer.md` § "What NOT to do" and the `agents-core:subagent-protocol` skill § "Recursive mitigation".

spec-workflow is the orchestrator; the implementer/reviewer subagents are leaves. This prevents recursive expansion if a sub-implementer is ever tempted to invoke spec-workflow itself.

## Quality bar

Before declaring done:

- Every `spec.md` success criterion has at least one matching `tasks.md` entry.
- Every task is either mapped to a commit or documented as a decision in `review.md`.
- `review.md` has at least one iteration ending in `PASS`.
- No runtime-specific or project-foreign assumptions leaked into the artifacts (the playbook is portable; the artifacts must stay portable too).
