# Align

## Purpose

Check a proposed feature or change against the project's `PROJECT.md` before non-trivial work begins. Reports one of three verdicts — ALIGNED, NEEDS_CLARIFICATION, OUT_OF_SCOPE — with evidence from the file. The skill is a methodology, not a verdict-issuing service: the user remains in the loop on every meaningful judgment.

This sits at the front of the adversarial review pipeline. `align` runs before planning. `planning-workflow` runs before implementation. `plan-critique` runs against the plan. `spec-validator` runs against the implementation. `security-auditor` runs against the diff. Each layer catches a different class of mistake.

## When to use

Invoke `/align` for:

- non-trivial features (multiple files, multiple plausible approaches)
- work where scope feels uncertain or the user is exploring
- any feature whose value or fit you cannot articulate in one sentence against the project's goals
- before `planning-workflow` for any change that warrants a plan

Skip `/align` for:

- mechanical changes (rename, typo, dep bump, formatting)
- bug fixes against documented behavior
- work whose alignment is obvious by inspection of `PROJECT.md`

Skipping is fine. Skipping silently on a non-trivial feature is not.

## Prerequisite: a filled `PROJECT.md`

`/align` requires `PROJECT.md` at the repo root, with at least these sections filled:

- `## Vision`
- `## Goals`
- `## Out of scope`

If `PROJECT.md` does not exist or those sections are still scaffolding (`<Replace...>` placeholders), stop and tell the user:

> `PROJECT.md` is required for `/align`. Copy the template (`cp _base/PROJECT.md.template PROJECT.md`) and fill in at least Vision, Goals, and Out of scope. The other sections (Constraints, Current phase, Known limitations) sharpen the verdict but are not required.

Do not invent goals or scope on the user's behalf. The point of the file is that the user owns those decisions.

## Process

| Step | What |
|---|---|
| 1 | Read `PROJECT.md` |
| 2 | Restate the proposed change in one sentence |
| 3 | Compare on three axes |
| 4 | Issue a verdict with cited evidence |
| 5 | On OUT_OF_SCOPE, present three options |

### 1. Read `PROJECT.md`

Read the file end-to-end. Identify the goals (bulleted), the explicit out-of-scope items, and the constraints. If `Current phase` or `Known limitations` exist, note them — they may sharpen the verdict but do not change the verdict mapping.

### 2. Restate the proposed change

Write the proposed change in one neutral sentence. Strip the user's framing — "we should add X" becomes "adds X". This makes the comparison mechanical rather than rhetorical.

### 3. Compare on three axes

For each axis, record evidence (specific lines from `PROJECT.md`) and a binary judgment.

**Goal alignment** — does the change advance one of the stated goals?
- **Yes** — name the goal(s) it advances.
- **Partial** — it advances a goal but also pulls in scope outside that goal.
- **No** — it does not advance any stated goal. This is rarely fatal on its own (the project may have legitimate non-goal work like refactoring), but it raises the bar.

**Scope** — is the change explicitly in the Out of scope list?
- **Yes** — name the out-of-scope item. This is the strongest possible signal of misalignment.
- **No** — note that explicitly; do not leave the axis unchecked.

**Constraints** — does the change violate any constraint?
- **Yes** — name the constraint and the violation. This is usually fatal.
- **No** — note explicitly.

### 4. Issue a verdict

Apply this mapping:

| Conditions | Verdict |
|---|---|
| Goal aligned (yes or partial), no scope hit, no constraint violation | **ALIGNED** |
| Goal alignment unclear, OR the change touches an ambiguous area in PROJECT.md, OR the comparison surfaces a missing entry | **NEEDS_CLARIFICATION** |
| Scope hit (yes), OR constraint violation (yes) | **OUT_OF_SCOPE** |

A goal that is "No" without any scope hit or constraint violation is usually NEEDS_CLARIFICATION, not OUT_OF_SCOPE — the project may simply have a goal it has not articulated yet.

### 5. On OUT_OF_SCOPE, present three options

When the verdict is OUT_OF_SCOPE, do not proceed silently and do not pretend to "find a way to make it fit." Present the user with three options and wait for their decision:

- **(a) Update `PROJECT.md`** — bring the feature into scope by editing the file. This is a legitimate response when the project has genuinely outgrown its earlier scoping. The user makes the edit (or approves the agent making it); the agent does not silently rewrite `PROJECT.md`.
- **(b) Adjust the feature** — describe a smaller or differently-shaped version that fits current scope. Useful when the feature is a wedge for a larger out-of-scope ambition.
- **(c) Cancel and discuss scope first** — no implementation. Useful when the scope conflict is real and the project should resolve it before any code is written.

All three are valid. Silent drift (do the work without resolving the conflict) is not.

## Output template

```
## /align verdict: ALIGNED | NEEDS_CLARIFICATION | OUT_OF_SCOPE

## Proposed change (restated)
<one neutral sentence>

## Goal alignment: yes | partial | no
- Advances: <goal name, cited from PROJECT.md>
- Notes: <if partial or no, explain>

## Scope: clear | hit
- Out-of-scope items checked: <list>
- Hits: <named item, if any>

## Constraints: clear | violated
- Constraints checked: <list>
- Violations: <named constraint, if any>

## Notes from current phase / known limitations
- <anything relevant; or "none">

## Options (OUT_OF_SCOPE only)
- (a) Update PROJECT.md: <what would need to change in the file>
- (b) Adjust the feature: <what a fit-within-scope version would look like>
- (c) Cancel: discuss scope before any implementation

## What I need from you (NEEDS_CLARIFICATION or OUT_OF_SCOPE only)
<concrete question(s) or option choice>
```

## Failure modes to prevent

- **Inventing goals on the user's behalf.** If `PROJECT.md` does not name a goal that would justify the change, do not invent one. NEEDS_CLARIFICATION is the right verdict.
- **Soft verdicts.** "Mostly aligned with minor concerns" is not a valid verdict — it is a refusal to choose. Pick one of ALIGNED / NEEDS_CLARIFICATION / OUT_OF_SCOPE and explain the evidence.
- **Silent PROJECT.md edits.** Updating the alignment doc is a legitimate option but requires explicit user approval. An agent that rewrites `PROJECT.md` to make a feature fit is doing the wrong thing.
- **Skipping the file read.** "I checked alignment based on context" is not the same as reading `PROJECT.md`. Read the file. Cite the lines.
- **Using `/align` as a permission slip.** ALIGNED is not "go build whatever". The verdict says the *direction* is right; `planning-workflow` and downstream skills still apply to the *shape*.

## When `/align` says ALIGNED

Proceed to the next step. For non-trivial work that is the `planning-workflow` skill. For trivial work it is just implementation. The `/align` verdict travels with the work (mention it in the plan, the task, or the commit body when useful) so reviewers can see the basis for the decision.

## When `/align` says NEEDS_CLARIFICATION or OUT_OF_SCOPE

Stop. Ask the questions or present the options. Do not loop back to "align it again with adjusted framing" until the underlying question is settled. Repeated `/align` invocations with rephrased descriptions to chase ALIGNED are a known anti-pattern — the verdict is a signal, not an obstacle to route around.
