---
name: execute-plan
description: "Execute an approved task or implementation plan phase-by-phase as a thin orchestrator: each phase is implemented by a fresh subagent and reviewed by separate spec, quality and security reviewers, every phase is committed, and run state on disk lets a later session resume. Use when the user says \"execute plan\" or \"execute-plan\", explicitly invokes this skill, or points to docs/tasks_manager/_todos/<TASK>.md or docs/_plans/<slug>.md and wants it implemented."
argument-hint: "Which task file, plan file, or approved plan should I execute?"
metadata:
  source: playbooks/skills/engineering/execute-plan.md
  pack: core
---

# Execute Plan

## Purpose

Execute an already-approved task or implementation plan with phase discipline, per-phase commits,
required checks, and independent review before declaring the work satisfactory — without letting the
whole execution pile up in one context window.

You are the **orchestrator**. You read the task file, the run state, and short verdicts; you dispatch
one fresh implementer per phase and separate reviewers per phase; you own every commit. You do not
implement phases yourself unless the runtime has no subagents (see step 0). Everything larger than a
verdict lives in `docs/tasks_manager/_runs/<TASK-ID>/` and travels as a file path, so a fresh session
can pick the run up from disk.

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
the `agents-core:squash-workspace-commits` skill.

The dispatch rules, status vocabulary, fix-loop cap and `Ruling:` format come from the
`agents-core:subagent-protocol` skill; this skill only says when to apply them.

## Required outcome

The implementation is satisfactory only when all of these are true:

- Every phase acceptance criterion is met.
- Required unit, integration, and explicitly requested e2e checks pass.
- Each completed phase has its own commit, made by the orchestrator, and a `committed` row with its
  SHA in `_runs/<TASK-ID>/state.md`.
- Each phase passed a spec review and a quality review from separate reviewers (plus a security
  review when the phase touched a security surface), or every open finding carries a `Ruling:` line.
- One final whole-task review reports no blocking or acceptance-failing findings.
- Any residual concerns are recorded as non-blocking.

If a phase does not converge within the fix-loop cap, or the final review does not converge in one
fix wave, stop and report the remaining issues instead of looping.

## Process

### 0. Detect the runtime

Decide once, record it as `runtime:` in the run state (step 3), and follow the matching reference for
every dispatch in steps 4–7. Do not guess: if you cannot name the tool you would call to start a
subagent, you are inline.

- `claude` — you can dispatch named subagents (`implementer`, `reviewer`, `security-auditor`,
  `spec-validator`, `plan-critic`) and resume one by its id: follow
  [references/runtime-claude.md](references/runtime-claude.md).
- `codex` — you can spawn agents from the project's `.codex/agents/*.toml` roles but cannot resume a
  finished one by id: follow [references/runtime-codex.md](references/runtime-codex.md).
- `inline` — no subagent tool, or the user asked for inline execution: follow
  [references/inline-execution.md](references/inline-execution.md). Every review is labelled
  "not independent" in the execution log, and the run state is still written so a later session
  with subagents can resume.

The runtime never changes the phase loop, the run-state files, or the commit rules below; only the
dispatch and resume mechanics differ. When no session should hold the run at all, `at task run
<TASK-ID>` executes steps 3–7 from a shell with the same files ([references/run-state.md](references/run-state.md)
§"Scripted driver"); it stops at the fix-loop cap for a human or agent to adjudicate. A pasted plan or a `docs/_plans/` file without the
`agents-tasks` plugin uses the same loop with hand-written briefs
([references/run-state.md](references/run-state.md) §"Without agents-tasks").

### 1. Resolve and normalize the input

Read the task or plan file before editing. Extract:

- phase list and phase boundaries
- phase-level and whole-plan acceptance criteria
- task-local `### Specification` / `### Design` sections and any `Spec refs` metadata
- required checks, including related tests and any explicit e2e requirements
- expected files, components, and user-facing behavior
- where progress should be recorded

**Resume check.** If `docs/tasks_manager/_runs/<TASK-ID>/state.md` already exists, this is a resumed
run: follow [references/run-state.md](references/run-state.md) §"Resume" (verify every recorded
commit exists, re-read `Ruling:` and `Interface:` lines, continue at the first row that is not
`committed`). Never re-run a committed phase; never rebuild the state file from chat memory.

For task files, use the existing `## Execution log` and phase checklists. For `docs/_plans` files,
update phase checkboxes if present; if no execution log exists, append a lightweight `## Execution log`
section. For pasted plans, first write or update a durable plan/task file with phases, acceptance
criteria, and checks, then continue from that file.

If phases, acceptance criteria, or checks are missing, normalize the plan before implementation. If the
normalization changes scope or creates new product decisions, ask the user to approve the normalized
plan. If it only clarifies obvious execution mechanics, record the clarification in the execution log
and proceed.

For task files, resolve spec sources before treating the task as executable:

1. Task-local `### Specification` and `### Design`.
2. `Spec refs` metadata, including `self`, PRDs, plans, `docs/resources/system-map.md`, area summaries,
   dependency graphs, component contexts, and feature contracts.
3. Acceptance criteria and related tests.
4. Relevant durable docs found during current-state review.
5. Current user instructions.

Record each source and lifecycle status in the execution log. `draft` and `accepted` specs are planned
intent. `implemented` specs are current-state evidence only when backed by code, tests, task history,
or reviewed docs. `partially-implemented` specs must be split into live behavior and remaining target
behavior. `superseded` specs must point to a replacement or be ignored with the uncertainty recorded.

### 2. Resolve repo branch policy and autonomy

Before any implementation phase, determine the repo scope, branch/work mode, and effective autonomy.
This is mandatory even when the task looks single-repo.

1. If `.config/repos.project.md` exists, read it and run `at repos-check`.
2. If the task or plan has `Repos` metadata, use those repo slugs as the execution scope. If no `Repos`
   metadata exists, treat the current repo as the execution scope.
3. If cross-repo execution requires local checkout paths, validate `.local/repos.map` with
   `at repos-check --local` before editing another checkout.
4. For each repo in scope, record the resolved `Default branch`, `Integration branch`, and
   `Work mode` in the execution log.
5. Resolve effective autonomy using the `agents-core:git-discipline` skill (references/autonomy-levels.md) and record the repo
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

Never create a new branch merely because `agents-core:execute-plan` will make commits.

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

### 3. Protect the worktree and open the run

Before any implementation phase:

1. Run `git status --short`.
2. Identify unrelated dirty changes.
3. If unrelated changes are outside the phase scope, leave them untouched and use explicit pathspecs
   when staging.
4. If unrelated changes are inside files the phase must edit, stop and ask how to proceed.
5. Record the execution base revision with `git rev-parse --short HEAD` in the task/plan execution
   log.
6. Open the run state (skip on a resumed run):

   ```bash
   at task run-state init <TASK-ID> --base <rev> --branch <branch> --work-mode <mode> --autonomy <L?> --runtime <claude|codex|inline>
   ```

   Without `agents-tasks`, write `state.md` by hand from the format in
   [references/run-state.md](references/run-state.md).

Never use destructive cleanup to get a clean tree. Work with existing changes or ask when they collide
with the phase.

### 4. Run the pre-implementation architect review

Before code execution, run an architect review over the plan and affected code. The goal is to catch
bad phase boundaries, poor system fit, risky dependencies, and inadequate tests before implementation
creates churn.

Dispatch a read-only `plan-critic` on the strongest available model with the architecture brief from
[references/briefs.md](references/briefs.md) §"Architecture review", per the runtime reference.
Inline: perform a documented main-thread architecture review and label it as not independent.

If the verdict is `BLOCKED`, stop and ask the user or fix the plan before implementation. If the
verdict is `REVISE`, update the plan/execution log, rerun or explicitly reconcile the review, and only
then proceed. Do not bury architecture findings as implementation details.

For existing task files, this review can satisfy or extend the task-system pre-implementation
plan-critic review when it covers freshness and applicability. If a separate researcher current-state
review is required by the task convention, run and log that bounded review before code edits as well.

### 5. Orchestrate one phase at a time

For each phase whose `state.md` row is not `committed`, in order. Keep your own context to paths,
verdict blocks and the state file; never open a report, diff or test log that a subagent wrote unless
you are adjudicating a finding.

1. **Gate.** Re-check `git status --short`. Run the baseline/relevant checks for the phase; if required
   checks already fail, stop unless the failure is clearly unrelated and recorded as an accepted
   baseline condition.
2. **Brief.** `at task brief <TASK-ID> --phase N` writes
   `_runs/<TASK-ID>/phase-N/brief.md` (without `agents-tasks`, write it by hand with the same
   headings). Append under `## Orchestrator notes`: work mode and autonomy, the **scope fence** (files
   and directories this phase may touch), every `Interface:` and `Ruling:` line from `state.md`, and
   any clarification from step 1. Implement only that phase; if the brief would need work from a later
   phase, update the plan first.
3. **Mark.** Set the row to `implementing`, `Attempt` +1, and record `BASE=$(git rev-parse --short HEAD)`
   as a `Phase N:` line.
4. **Implement.** Dispatch a fresh `implementer` with the dispatch prompt from
   [references/briefs.md](references/briefs.md) §"Implementer". On `NEEDS_CONTEXT`, answer inside the
   brief's orchestrator notes and re-dispatch; on `BLOCKED`, triage per `agents-core:subagent-protocol`.
   Never re-dispatch an identical prompt.
5. **Package.** `git diff <BASE> -- <scope fence> > _runs/<TASK-ID>/phase-N/diff.patch` (git-ignored,
   regenerable). Set the row to `reviewing`.
6. **Review in parallel**, all read-only. Reviewers cannot write files, so each reply *is* the report:
   save it verbatim to its file, then keep only the verdict block in mind.
   - `reviewer` with `Stage: spec` → `review-spec.md`
   - `reviewer` with `Stage: quality` → `review-quality.md`
   - `security-auditor` → `review-security.md`, only when the phase touches a **security surface**:
     auth or sessions, input parsing or deserialization, subprocess/shell/file-path handling,
     network or HTTP, secrets/config/env, permissions or ACLs, SQL or query building, crypto, CI or
     hook configuration, new dependencies. Otherwise write `n/a` in the `Security` cell.
   Record each `Verdict` and findings count in the row.
7. **Fix loop.** While any verdict is `FAIL` or a critical finding is open, run the fix loop from
   `agents-core:subagent-protocol` (cap: three rounds). Write the numbered open findings to
   `phase-N/findings-R.md`, hand that path to the implementer with the round prompt from briefs.md, set
   the row to `fixing`, then re-review only those findings against the fix diff (save the reply as
   `phase-N/re-review-R-<stage>.md`). A spec `FAIL` is fixed before quality findings are acted on.
8. **Adjudicate at the cap.** Decide each still-open finding yourself and record a `Ruling:` line in
   `state.md`; small defects you can fix in a few lines, you fix and rule. If every path forward is a
   guess, set the row to `blocked`, write what is needed, and stop.
9. **Verify and record.** Run the phase checks and related tests yourself and read the output. Tick the
   phase checkboxes, update `Updated` and `Last executed`, and append a **≤ 10-line** execution-log entry:
   what changed, the verdicts, any rulings, and the pointer `see docs/tasks_manager/_runs/<TASK-ID>/phase-N/`.
   Add any interface later phases depend on as an `Interface:` line in `state.md`. Run `at ledger sync`
   so the regenerated ledgers ride in the phase commit.
10. **Commit.** Stage with explicit pathspecs — the scope fence, the task/plan file, and
    `docs/tasks_manager/_runs/<TASK-ID>/` — never `git add -A`. Use the phase commit format below.
11. **Close the row.** Write the SHA, set `committed`, bump `current_phase`, `updated`. Then
    `at ledger check` and `at task run-state check <TASK-ID>`.

Phase commit format:

```text
<type>: <phase outcome>

What changed:
- <concise summary>

Why:
- <phase acceptance or user outcome>

Checks:
- <command>: <result>
- reviews: spec <PASS|FAIL>, quality <PASS|FAIL>, security <PASS|FAIL|n/a>; rulings: <n>
```

Infer `<type>` conservatively (`feat`, `fix`, `chore`, `docs`, `test`, or `refactor`). If commit hooks
fail, fix the issue (yourself, or through a fix-round dispatch) and rerun the required checks before
committing. Never proceed to the next phase with failing required tests. Never commit a phase whose
acceptance criteria are unmet, or whose row still has an unruled open finding.

For task files, progress updates are not optional: update phase checkboxes, `Updated`, `Last executed`,
and the append-only execution log before considering the phase complete. If a phase changes code and
the task file is not updated, the phase is not ready to commit.

### 6. Run final validation

After all phases are committed:

1. Run the final required checks from the plan/task.
2. Run e2e only at the end unless a phase explicitly requires e2e earlier.
3. Optionally dispatch `spec-validator` over **all** acceptance criteria (report path
   `_runs/<TASK-ID>/validation.md`) when the criteria are behavioral enough to test spec-blind; it is
   too heavy per phase and runs once here.
4. Fix failures until required checks pass or a real blocker is reached.
5. Commit final validation fixes or execution-log-only updates if they were not included in the last
   phase commit.

If e2e is marked `N/A`, record why. If the project has no e2e command and the plan did not require one,
do not invent a heavyweight e2e harness; record the available validation instead.

### 7. Run the final whole-task review

Per-phase reviews saw one diff each; this round looks at the whole. Dispatch two read-only `reviewer`
subagents in parallel with `Stage: both`, on the strongest available model, using the whole-task brief
from [references/briefs.md](references/briefs.md) §"Final review"; save the replies as
`_runs/<TASK-ID>/final-review-1.md` and `-2.md`. They must not see each other's reports.

Outcomes:

- Both `Verdict: PASS` with no critical findings: record the result and finish.
- Only non-critical findings: record them explicitly as non-blocking and finish.
- Any `FAIL`, critical finding, or `BLOCKED`: **one** fix wave — merge the open findings into
  `_runs/<TASK-ID>/final-findings.md`, dispatch one implementer (fresh, strongest model) with the
  round-3 prompt, commit as `fix: address execute-plan final review`, then **one** scoped re-review of
  those findings. If it still fails, stop: report the remaining issues, last passing checks, and why the
  loop did not converge. No second fix wave.

Inline: a documented main-thread review labelled "not independent"; ask the user whether to accept it
or to rerun in an environment with subagents.

### 8. Optionally squash completed task commits

After all implementation phases, final validation, and the final review pass, downstream repos may
squash the task's own step commits into one final task commit. This is a cleanup step after the task is
done; do not squash early because phase commits are the review and recovery boundary during execution.

Route the cleanup through the `agents-core:squash-workspace-commits` skill. That skill owns
the audit helper, pushed/shared-history refusal, unrelated-commit preservation rules, backup-ref
requirements, and final squashed commit-message requirements.

For multi-repo tasks, audit and squash independently per downstream repo. Do not squash read-only repos,
repos outside the task scope, or upstream template-maintenance history unless the user explicitly asks.

The run directory stays until `agents-tasks:complete-task` copies its rulings into the completion
summary and removes it.

## Limits

- **One checkout per run.** The loop diffs, reviews and commits in the repository that holds the
  task file. A task whose `Repos` metadata spans several repos is executed as one run per repo, in
  the order the task's phases require; step 2 only decides which repos are in scope.
- **Phases run in order.** There is no wave parallelism for independent phases; a phase starts when
  the previous one is committed, so `Interface:` lines are always complete.
- **Implementers execute what they read.** An implementer with edit and Bash approval acts on the
  repository's content, including anything injected into it; the plugin hooks gate dangerous git,
  shell and secret paths, nothing else. For a repository you do not trust, run implementers in the
  worktree isolation from [references/runtime-claude.md](references/runtime-claude.md) and review the
  diff package before it reaches the main tree.

## Quality bar

- The plan/task remains the source of truth; implementation notes do not replace acceptance criteria.
- `_runs/<TASK-ID>/state.md` is the source of truth for resume; subagent ids are an accelerator, never
  a requirement. A fresh session must be able to continue from the file alone.
- The orchestrator's context holds paths and verdicts, not report bodies, diffs, or test logs.
- Each phase is independently reviewable from its commit and its `phase-N/` directory.
- If task commits are squashed, the final commit message preserves the phase/review/check summary.
- Required checks are named with exact commands and outcomes, run by the orchestrator, not taken from
  an implementer's report.
- E2e timing follows the plan: end-only by default, earlier only when explicitly required.
- Unrelated work is neither staged nor committed.
- Subagent availability is represented honestly; fallback reviews are labeled as fallback reviews.
- Every finding that was not fixed has a `Ruling:` line a later reader can audit.
