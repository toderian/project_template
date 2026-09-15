# Dispatch prompts

Every prompt below is self-contained: the subagent inherits nothing from your session. Paths are
repo-relative. Replace `<…>`; delete lines that do not apply. Keep the prompt short — the brief file
carries the requirements, the prompt carries the contract. Implementers write their own report file;
reviewers are read-only, so their reply is the report and **you** save it to the path the prompt names.

## Architecture review (step 4, `plan-critic`, read-only)

```text
Task description: Review this approved implementation plan before execution.
Acceptance criteria:
- The plan fits the existing architecture and local patterns.
- Phase boundaries are independently committable and do not hide cross-phase dependencies.
- Test strategy is sufficient for the stated acceptance criteria.
- Resolved specs are classified as planned intent vs implemented evidence before code edits.
- Risks, migrations, rollout concerns, and compatibility constraints are identified.
Scope fence: read-only; do not edit files.
Context files: <plan/task file>, affected source files, relevant tests, component docs if present.
Model hint: strongest available.
Your reply is the review (I save it to docs/tasks_manager/_runs/<TASK-ID>/architecture-review.md); at most 40 lines ending in:
## Status: DONE | DONE_WITH_CONCERNS | BLOCKED
## Architecture verdict: PROCEED | REVISE | BLOCKED
## Blocking findings: <count>, one line each
## Required plan changes: <one line each>
```

## Implementer (step 5.4, fresh `implementer`)

```text
Project: <one line: what this repo is and the command that runs its tests>.
Brief: docs/tasks_manager/_runs/<TASK-ID>/phase-N/brief.md — read this first; it is your full context.
Report path: docs/tasks_manager/_runs/<TASK-ID>/phase-N/report.md
Scope fence: <files/dirs you may touch>. Nothing else. Do not commit or stage. Do not spawn subagents.
Do not read AGENTS.md, CLAUDE.md, or other skills.
Interfaces and rulings from earlier phases are in the brief's orchestrator notes; honour them.
Run the checks named in the brief and record real output in the report.
Model hint: <default for the implementer card | strongest for round 3>.
Reply with at most 15 lines ending in the ## Status: block (DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED).
```

Never paste the task file, prior reports, or the conversation into this prompt.

## Reviewer (step 5.6, `reviewer`, read-only, one per stage)

```text
Stage: spec | quality | both
Brief: docs/tasks_manager/_runs/<TASK-ID>/phase-N/brief.md (requirements and acceptance criteria)
Diff: docs/tasks_manager/_runs/<TASK-ID>/phase-N/diff.patch (BASE <rev> → working tree)
Implementer report: docs/tasks_manager/_runs/<TASK-ID>/phase-N/report.md — treat its claims as unverified.
Scope fence: read-only; do not edit files. Run tests only to check a specific doubt.
Global constraints: <work mode, autonomy, anything the phase must not break>
Model hint: strongest available.
Your reply is the report (I save it to docs/tasks_manager/_runs/<TASK-ID>/phase-N/review-<spec|quality>.md):
the ## Status / ## Verdict / ## Findings block first, then ## Evidence; at most 40 lines.
```

## Security auditor (step 5.6, `security-auditor`, only on a security surface)

```text
Surface: <why this phase is a security surface: auth | input parsing | subprocess | network | secrets | permissions | queries | crypto | CI/hooks | new dependency>
Brief: docs/tasks_manager/_runs/<TASK-ID>/phase-N/brief.md
Diff: docs/tasks_manager/_runs/<TASK-ID>/phase-N/diff.patch
Scope fence: read-only; do not edit files.
Your reply is the audit (I save it to docs/tasks_manager/_runs/<TASK-ID>/phase-N/review-security.md):
the ## Status / ## Verdict / ## Findings block first, each finding as a numbered [C|I|M] path:line — one line, then the detail; at most 40 lines.
```

## Fix round R (step 5.7)

Rounds 1–2 go to the same implementer (resumed where the runtime allows, otherwise a fresh dispatch
with the same prompt); round 3 is a fresh implementer on the strongest model.

```text
Fix round <R> of 3 for phase N.
Open findings: docs/tasks_manager/_runs/<TASK-ID>/phase-N/findings-<R>.md — address every numbered item, nothing else.
Brief and scope fence are unchanged: docs/tasks_manager/_runs/<TASK-ID>/phase-N/brief.md.
Report path: docs/tasks_manager/_runs/<TASK-ID>/phase-N/report.md (append a "## Fix round <R>" section).
Do not commit. Do not widen the scope; report NEEDS_CONTEXT if a finding cannot be fixed inside it.
Reply with at most 15 lines ending in the ## Status: block.
```

Round-3 prefix: `A prior implementer attempted this phase twice; you own it now. Read the brief and
the findings file fresh; do not trust the earlier report sections.`

`findings-R.md` is the concatenated numbered `[C|I|M] path:line — one line` items from the reviewer
replies, spec findings first, with the source review path after each item.

## Scoped re-review (after each fix round)

Same reviewer card and stage as the original review, read-only:

```text
Re-review round <R> for phase N. Stage: <spec | quality | security>.
Findings under review: docs/tasks_manager/_runs/<TASK-ID>/phase-N/findings-<R>.md
Fix diff: <git diff <sha or BASE> -- <scope fence>, written to phase-N/fix-<R>.patch>
Judge only whether each numbered finding is resolved without a new defect; do not reopen the whole diff.
Your reply is the re-review (I save it to docs/tasks_manager/_runs/<TASK-ID>/phase-N/re-review-<R>-<stage>.md):
per finding "<n>: resolved | open — one line", then the ## Status / ## Verdict / ## Findings block; at most 40 lines.
```

## Final review (step 7, two `reviewer`s in parallel, `Stage: both`)

```text
Stage: both
Task description: Review the completed execution of this approved plan as a whole.
Acceptance criteria:
- All plan/task acceptance criteria are satisfied.
- The implementation satisfies every accepted/planned spec source resolved for this task.
- Current-state claims rely only on implemented or evidence-backed partially-implemented specs, code,
  tests, or task history.
- Required checks pass and are meaningful for the changed behavior.
- Phase commits are scoped and do not include unrelated cleanup.
- No blocking regressions, security issues, or maintainability problems remain.
Context: <plan/task file>, docs/tasks_manager/_runs/<TASK-ID>/state.md (rulings are decisions, not defects),
git diff <base_rev>..HEAD.
Scope fence: read-only; do not edit files.
Model hint: strongest available.
Your reply is the review (I save it to docs/tasks_manager/_runs/<TASK-ID>/final-review-<1|2>.md):
the ## Status / ## Verdict / ## Findings block first, then ## Evidence; at most 40 lines.
```

## Adjudication line (step 5.8)

Recorded in `state.md`, one per finding left open at the cap:

```text
Ruling: <finding, ≤ 1 line> — <fixed by orchestrator | accepted as-is | parked: <why>> — cost if wrong: <one clause>
```
