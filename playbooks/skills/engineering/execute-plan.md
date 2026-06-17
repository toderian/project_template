# Execute Plan

## Purpose

Execute an already-approved task or implementation plan with phase discipline, per-phase commits,
required checks, and independent implementation review before declaring the work satisfactory.

Use this skill when the user points to:

- `docs/tasks_manager/_todos/<TASK>.md`
- `docs/_plans/<slug>.md`
- a pasted plan that they want implemented now

This is an execution skill, not a planning skill. If the input is only a rough idea, PRD, or unapproved
proposal, route it through the appropriate planning or task skill first. A pasted plan is acceptable
only after it has been normalized into explicit phases, acceptance criteria, and tests/checks.

Invoking this skill is consent to create commits for completed phases. Do not ask again before each
normal phase commit, but do protect unrelated local work. In downstream repos, those phase/review
commits may be squashed after the task is complete and reviewed, following
`playbooks/skills/productivity/squash-workspace-commits.md`.

## Required outcome

The implementation is satisfactory only when all of these are true:

- Every phase acceptance criterion is met.
- Required unit, integration, and explicitly requested e2e checks pass.
- During execution, each completed phase has its own commit.
- Two independent xhigh implementation reviewers report no blocking or acceptance-failing findings.
- Any residual concerns are recorded as non-blocking.

If review fails three rounds, stop and report the remaining issues instead of looping indefinitely.

## Process

### 1. Resolve and normalize the input

Read the task or plan file before editing. Extract:

- phase list and phase boundaries
- phase-level and whole-plan acceptance criteria
- required checks, including related tests and any explicit e2e requirements
- expected files, components, and user-facing behavior
- where progress should be recorded

For task files, use the existing `## Execution log` and phase checklists. For `docs/_plans` files,
update phase checkboxes if present; if no execution log exists, append a lightweight `## Execution log`
section. For pasted plans, first write or update a durable plan/task file with phases, acceptance
criteria, and checks, then continue from that file.

If phases, acceptance criteria, or checks are missing, normalize the plan before implementation. If the
normalization changes scope or creates new product decisions, ask the user to approve the normalized
plan. If it only clarifies obvious execution mechanics, record the clarification in the execution log
and proceed.

### 2. Resolve repo branch policy and autonomy

Before any implementation phase, determine the repo scope, branch/work mode, and effective autonomy.
This is mandatory even when the task looks single-repo.

1. If `.config/repos.project.md` exists, read it and run `_base/scripts/check-repos-config.sh`.
2. If the task or plan has `Repos` metadata, use those repo slugs as the execution scope. If no `Repos`
   metadata exists, treat the current repo as the execution scope.
3. If cross-repo execution requires local checkout paths, validate `.local/repos.map` with
   `_base/scripts/check-repos-config.sh --local` before editing another checkout.
4. For each repo in scope, record the resolved `Default branch`, `Integration branch`, and
   `Work mode` in the execution log.
5. Resolve effective autonomy using `playbooks/conventions/autonomy-levels.md` and record the repo
   `Autonomy max`, task/user `Autonomy` request, effective level, and any stricter runtime or safety
   limit in the execution log.

Branch behavior by `Work mode`:

- `default-branch`: commit directly on the configured default branch. If the checkout is not on that
  branch, ask before continuing or switching.
- `same-branch`: stay on the current branch. Do not create or switch branches.
- `task-branch`: use the explicit branch named by the user, task, issue, or repo-specific
  `AGENTS.md`. If none is named, ask before creating or switching.
- `read-only`: do not edit or commit in that repo. Stop if the plan requires writes there.
- `ask`: ask before editing or changing branches.

If no `.config/repos.project.md` exists in a template-inherited downstream repo, resolve the repo's
default branch (`main` or `master` in most repos). If already on that branch, stay there. If currently
on a non-default branch, ask before continuing or switching. Do not create a feature/task branch unless
the user explicitly asked for it or the host/CI policy requires it. Downstream repos should accumulate
execute-plan commits on the approved same/default branch, with one coherent commit per phase.

Never create a new branch merely because `execute-plan` will make commits.

Autonomy behavior:

- Default to `L1` when no repo or task autonomy is configured.
- `L0` is read-only. Stop before edits, staging, commits, pushes, or connector writes.
- `L1` allows local edits, checks, iteration, and local commits inside this approved workflow.
- `L2` adds push/update and CI repair only for the branch allowed by effective `Work mode`.
- `L3` adds draft PR open/update and PR status validation only.
- No level authorizes merge, deploy, release, mark-ready-for-review, force-push/history rewrite,
  broad connector writes, or secret exposure.

Keep `Work mode` separate from autonomy: work mode decides where/how work happens; autonomy decides
how far the loop may proceed. If a later phase would push, repair CI, open/update a PR, or write to an
external connector, re-check and log that the effective autonomy permits that action before doing it.

### 3. Protect the worktree

Before any implementation phase:

1. Run `git status --short`.
2. Identify unrelated dirty changes.
3. If unrelated changes are outside the phase scope, leave them untouched and use explicit pathspecs
   when staging.
4. If unrelated changes are inside files the phase must edit, stop and ask how to proceed.
5. Record the execution base revision with `git rev-parse --short HEAD` in the task/plan execution
   log.

Never use destructive cleanup to get a clean tree. Work with existing changes or ask when they collide
with the phase.

### 4. Run the pre-implementation architect review

Before code execution, run an architect review subagent, or the closest architecture review facility
the runtime supports, over the plan and affected code. The goal is to catch bad phase boundaries, poor
system fit, risky dependencies, and inadequate tests before implementation creates churn.

Preferred dispatch:

- Claude Code: dispatch a read-only subagent with the strongest available model. If only named
  subagents are available, use `plan-critic` with the architecture brief below.
- Codex: use multi-agent/subagent tools when available. If no subagent runtime is available, perform a
  documented main-thread architecture review and label it as not independent.

Architecture review brief:

```text
Task description: Review this approved implementation plan before execution.
Acceptance criteria:
- The plan fits the existing architecture and local patterns.
- Phase boundaries are independently committable and do not hide cross-phase dependencies.
- Test strategy is sufficient for the stated acceptance criteria.
- Risks, migrations, rollout concerns, and compatibility constraints are identified.
Scope fence: read-only; do not edit files.
Context files: <plan/task file>, affected source files, relevant tests, component docs if present.
Model hint: strongest/xhigh available.
Report:
## Status: DONE | DONE_WITH_CONCERNS | BLOCKED
## Architecture verdict: PROCEED | REVISE | BLOCKED
## Blocking findings:
## Non-blocking risks:
## Required plan changes:
## Summary:
```

If the verdict is `BLOCKED`, stop and ask the user or fix the plan before implementation. If the
verdict is `REVISE`, update the plan/execution log, rerun or explicitly reconcile the review, and only
then proceed. Do not bury architecture findings as implementation details.

For existing task files, this review can satisfy or extend the task-system pre-implementation
plan-critic review when it covers freshness and applicability. If a separate researcher current-state
review is required by the task convention, run and log that bounded review before code edits as well.

### 5. Execute one phase at a time

For each phase, keep the loop narrow:

1. Re-check `git status --short` and protect unrelated changes.
2. Run the baseline/relevant checks listed for that phase. If required checks are already failing,
   stop unless the failure is clearly unrelated and recorded as an accepted baseline condition.
3. Implement only that phase. Do not pull future phase work forward unless the plan is updated first.
4. Run the phase checks and related tests.
5. Verify each phase acceptance criterion against observable behavior or code.
6. Update progress markers and append an execution log entry with actions, decisions, test results,
   and outcome.
7. Stage only files that belong to the phase.
8. Commit before moving to the next phase.
9. Record the phase commit SHA in the next execution-log update or closeout summary. Do not create an
   extra metadata-only commit solely to record the SHA unless the project explicitly wants that.

Phase commit format:

```text
<type>: <phase outcome>

What changed:
- <concise summary>

Why:
- <phase acceptance or user outcome>

Checks:
- <command>: <result>
```

Infer `<type>` conservatively (`feat`, `fix`, `chore`, `docs`, `test`, or `refactor`). If commit hooks
fail, fix the issue and rerun the required checks before committing. Never proceed to the next phase
with failing required tests. Never commit a phase whose acceptance criteria are unmet.

For task files, progress updates are not optional: update phase checkboxes, `Updated`, `Last executed`,
and the append-only execution log before considering the phase complete. If a phase changes code and
the task file is not updated, the phase is not ready to commit.

### 6. Run final validation

After all phases are committed:

1. Run the final required checks from the plan/task.
2. Run e2e only at the end unless a phase explicitly requires e2e earlier.
3. Fix failures until required checks pass or a real blocker is reached.
4. Commit final validation fixes or execution-log-only updates if they were not included in the last
   phase commit.

If e2e is marked `N/A`, record why. If the project has no e2e command and the plan did not require one,
do not invent a heavyweight e2e harness; record the available validation instead.

### 7. Run the two-reviewer validation loop

Run up to three review rounds. Each round dispatches two independent xhigh implementation reviewers.
They must not see each other's reports before both have returned.

Reviewer dispatch rules:

- Claude Code: dispatch two read-only `reviewer` subagents in parallel with the strongest available
  model/configuration.
- Codex: use multi-agent/subagent tools when available. If no subagent runtime is available, do not
  pretend independent xhigh review occurred. Stop and ask the user whether to accept a documented
  main-thread fallback review or to run in an environment with subagent support.

Implementation review brief:

```text
Task description: Review the completed execution of this approved plan.
Acceptance criteria:
- All plan/task acceptance criteria are satisfied.
- Required checks pass and are meaningful for the changed behavior.
- Phase commits are scoped and do not include unrelated cleanup.
- No blocking regressions, security issues, or maintainability problems remain.
Scope fence: read-only; do not edit files.
Context files: <plan/task file>, execution log, relevant source/tests, git diff <base>..HEAD.
Model hint: strongest/xhigh available.
Report:
## Status: DONE | DONE_WITH_CONCERNS | BLOCKED
## Spec compliance: PASS | FAIL
## Blocking findings:
## Non-blocking concerns:
## Checks reviewed:
## Summary:
```

Review outcomes:

- If both reviewers report `Spec compliance: PASS` and no blocking findings, record the review result
  and finish.
- If reviewers raise only non-blocking concerns, record them explicitly and finish.
- If either reviewer reports acceptance failure, blocking findings, or `BLOCKED`, fix the actionable
  findings, rerun relevant and final required checks, commit the fixes as
  `fix: address execute-plan review round <N>`, and start the next review round.
- After three failed rounds, stop. Report remaining issues, last passing checks, and why the loop did
  not converge.

### 8. Optionally squash completed task commits

After all implementation phases, final validation, and reviewer rounds pass, downstream repos may
squash the task's own step commits into one final task commit. This is a cleanup step after the task is
done; do not squash early because phase commits are the review and recovery boundary during execution.

Route the cleanup through `playbooks/skills/productivity/squash-workspace-commits.md`. That skill owns
the audit helper, pushed/shared-history refusal, unrelated-commit preservation rules, backup-ref
requirements, and final squashed commit-message requirements.

For multi-repo tasks, audit and squash independently per downstream repo. Do not squash read-only repos,
repos outside the task scope, or upstream template-maintenance history unless the user explicitly asks.

## Quality bar

- The plan/task remains the source of truth; implementation notes do not replace acceptance criteria.
- Each phase is independently reviewable from its commit.
- If task commits are squashed, the final commit message preserves the phase/review/check summary.
- Required checks are named with exact commands and outcomes.
- E2e timing follows the plan: end-only by default, earlier only when explicitly required.
- Unrelated work is neither staged nor committed.
- Subagent availability is represented honestly; fallback reviews are labeled as fallback reviews.
