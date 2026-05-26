# Planning Workflow

## Purpose

Produce a small, well-grounded plan before implementation so the wrong solution gets caught before any code is written.

Use this for any change that touches multiple files, has multiple plausible approaches, or where scope needs to be bounded explicitly. Skip it for one-line fixes or single-file edits with an obvious shape.

## The seven steps

| Step | Name | Output |
|---|---|---|
| 1 | Problem statement | why, scope, success criteria |
| 2 | Scope check | file estimate and a halt rule |
| 3 | Existing solutions | what already exists, in the codebase and the world |
| 4 | Minimal path | smallest change that gets there |
| 5 | Adversarial critique | plan reviewed against the plan-critique rubric |
| 6 | Decomposition | break into trackable units if multi-phase |
| 7 | Plan output | written file the implementer can follow |

### 1. Problem statement

Capture three things:

- **Why** the change is needed — the underlying problem, not the surface request
- **Scope** boundary — what is IN, what is explicitly OUT
- **Success criteria** — how anyone can tell when this is done

A problem statement without explicit OUT-of-scope items is incomplete. Most scope creep starts with an empty OUT list.

### 2. Scope check

Estimate the number of files affected. If during planning the count climbs past 1.5x the initial estimate, halt and re-scope before continuing. Scope creep caught at plan time is cheap. Caught at review time it is not.

### 3. Existing solutions

Look first, build second:

- **Codebase** — grep and glob for similar patterns, conventions, or prior implementations
- **Outside** — search for libraries, RFCs, or reference implementations from authoritative sources
- **Document what was searched** even when nothing turned up — proves the work was done and lets the next reader skip the same search

The single most common plan defect is "build something that already exists."

### 4. Minimal path

Design the smallest change that achieves the goal:

- which files must change, which can stay
- what order they should change in
- what can be deferred to a follow-up without breaking the immediate outcome

Default to subtraction. Every new file, abstraction, or dependency needs a reason.

### 5. Adversarial critique

Run the plan through the rubric in `playbooks/conventions/plan-critique.md`. The reviewer scores it on five axes (assumption audit, scope creep, existing solutions, minimalism, uncertainty), then issues PROCEED, REVISE, or BLOCKED. Plans below the PROCEED threshold are revised, not waved through.

When dispatching to a subagent for critique, use `.claude/agents/plan-critic.md`. Otherwise apply the rubric on the main thread under the critic personality (`playbooks/personalities/critic.md`).

### 6. Decomposition

If the plan covers multiple independent slices, break them into trackable units. Use `prd-to-todos` (for `docs/tasks_manager/_todos/`) or `prd-to-issues` (for GitHub). Each slice should be independently shippable.

### 7. Plan output

Write the plan to a durable location:

- ephemeral / discussion-stage plans → keep in the conversation
- plans that will outlive a session → `docs/_plans/<slug>.md`, or attach to a todo file under its `Phases` section per `todo-convention.md`

## Required plan sections

Every written plan contains, at minimum:

1. **Why + scope** — the problem and the in/out boundary
2. **Existing solutions** — what was searched, what was found
3. **Minimal path** — the smallest set of changes
4. **Risks and unknowns** — what might go wrong
5. **Critique history** — verdicts received and resolutions

## When to skip

Skip the formal workflow for changes that are:

- single-file, under ~50 lines
- mechanical (rename, typo fix, dep bump)
- already covered by an existing plan or todo

Skipping is fine. Skipping silently when the change is non-trivial is not.
