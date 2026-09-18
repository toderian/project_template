---
name: execute-plan
description: "Execute an approved task or implementation plan phase-by-phase with a committed run state on disk: small tasks are implemented in the main thread with one independent reviewer per phase, large ones as a thin orchestrator dispatching a fresh implementer and separate spec, quality and security reviewers per phase; every phase is committed and a later session can resume. Use when the user says \"execute plan\" or \"execute-plan\", explicitly invokes this skill, or points to docs/tasks_manager/_todos/<TASK>.md or docs/_plans/<slug>.md and wants it implemented."
argument-hint: "Which task file, plan file, or approved plan should I execute?"
metadata:
  source: playbooks/skills/engineering/execute-plan.md
  pack: core
---

# Execute Plan

## Purpose

Execute an already-approved task or implementation plan with phase discipline, per-phase commits,
required checks, and independent review before declaring the work satisfactory — at the smallest
scale that still gives an independent verdict.

Everything larger than a verdict lives in `docs/tasks_manager/_runs/<TASK-ID>/` and travels as a
file path, so a fresh session can pick the run up from disk. In **small** mode you implement each
phase yourself and one reviewer checks it. In **large** mode you are a thin orchestrator: you
dispatch one fresh implementer per phase and separate reviewers, and you own every commit.

Use this skill when the user points to `docs/tasks_manager/_todos/<TASK>.md`, `docs/_plans/<slug>.md`,
or a pasted plan they want implemented now. It is an execution skill: a rough idea, PRD, or
unapproved proposal goes through the planning or task skills first, and a pasted plan is accepted
only once it has explicit phases, acceptance criteria, and checks.

Invoking this skill is consent to create commits for completed phases. Do not ask again before each
normal phase commit, but do protect unrelated local work. Downstream repos may squash the phase
commits after the task is complete and reviewed (`agents-core:squash-workspace-commits`).

The dispatch rules, status vocabulary, fix-loop cap and `Ruling:` format come from the
`agents-core:subagent-protocol` skill; this skill only says when to apply them.

## Required outcome

- Every phase acceptance criterion is met and the required checks pass.
- Each completed phase has its own commit, made by you, and a `committed` row with its SHA in
  `_runs/<TASK-ID>/state.md`.
- Each phase passed an independent review (one `Stage: both` reviewer in small mode; separate spec
  and quality reviewers, plus security when the phase touched a security surface, in large mode),
  or every open finding carries a `Ruling:` line.
- The final whole-task review reports no blocking or acceptance-failing findings.
- Residual concerns are recorded as non-blocking.

If a phase does not converge within the fix-loop cap, or the final review does not converge in one
fix wave, stop and report the remaining issues instead of looping.

## Process

### 0. Pick the rung

| Rung | When | What runs |
|---|---|---|
| trivial | a one-sentence diff, not a tracked task | not this skill: edit, test, commit (`agents-core:tdd`) |
| **small** | ≤ 2 phases, scope fence ≤ ~10 files, no large trigger | you implement each phase; one `reviewer` with `Stage: both` per phase; one final reviewer when there were 2 phases |
| **large** | any large trigger | thin orchestrator: `plan-critic` architecture review, fresh `implementer` per phase, parallel spec + quality reviewers, conditional `security-auditor`, two final reviewers |
| program | too big for one task, way ahead unclear | `agents-tasks:wayfinder`; each resulting task runs its own rung |

**Large triggers** — any one is enough; record which in `state.md` as `mode_reason:`:

- ≥ 3 phases, or a phase whose scope fence exceeds ~10 files;
- a security surface (auth or sessions, input parsing or deserialization, subprocess/shell/file-path
  handling, network or HTTP, secrets/config/env, permissions or ACLs, SQL or query building, crypto,
  CI or hook configuration, new dependencies), a data migration, a public interface or contract, or
  more than one repo (`Repos` row);
- a `### Design` section or `Spec refs` other than `self`;
- `Execution: orchestrated` in the task metadata, or the user asks for full review;
- a small run's phase blows its context or exhausts its fix loop → escalate mid-run: set
  `mode: large`, dispatch a fresh implementer for the current phase from the existing brief, continue.

A run never de-escalates. Write `mode:` and `mode_reason:` into `state.md` when you open it (step 3).

Then detect the **runtime** and record it as `runtime:`; if you cannot name the tool you would call
to start a subagent, you are inline:

- `claude` — named subagents (`implementer`, `reviewer`, `security-auditor`, `spec-validator`,
  `plan-critic`), resumable by id: [references/runtime-claude.md](references/runtime-claude.md).
- `codex` — agents from `.codex/agents/*.toml`, no resume by id:
  [references/runtime-codex.md](references/runtime-codex.md).
- `inline` — no subagent tool: [references/inline-execution.md](references/inline-execution.md).
  Small mode with self-review labelled "not independent"; the run state is still written so a later
  session with subagents can resume and review properly.

The rung and runtime change who implements and who reviews; the phase loop, run-state files and
commit rules below are the same. `at task run <TASK-ID> [--mode small|large|auto]` executes steps 3–7
from a shell with the same files ([references/run-state.md](references/run-state.md) §"Scripted
driver"). A pasted plan or a `docs/_plans/` file without `agents-tasks` uses the same loop with
hand-written briefs (§"Without agents-tasks" there).

### 1. Resolve and normalize the input

Read the task or plan file. Extract the phase list, phase-level and whole-plan acceptance criteria,
task-local `### Specification` / `### Design` and `Spec refs`, required checks (related tests, any
explicit e2e requirement), the expected files and user-facing behavior, and where progress is recorded.

**Resume check.** If `docs/tasks_manager/_runs/<TASK-ID>/state.md` exists, this is a resumed run:
follow [references/run-state.md](references/run-state.md) §"Resume" (verify every recorded commit
exists, re-read `Ruling:` and `Interface:` lines, continue at the first row that is not `committed`).
Never re-run a committed phase; never rebuild the state file from chat memory.

Task files use their `## Execution log` and phase checklists (the first execution appends the log
section). `docs/_plans` files get their checkboxes ticked and a lightweight `## Execution log` if none
exists. A pasted plan is first written to a durable plan/task file with phases, criteria and checks.

If phases, acceptance criteria, or checks are missing, normalize the plan before implementation. A
normalization that changes scope or creates product decisions needs the user's approval; one that
only clarifies execution mechanics is recorded in the execution log.

For task files, resolve the spec sources in the order given by the `agents-tasks:task-ledger` skill
(references/spec-lifecycle.md) and record each source and its status in one execution-log line:
`draft` / `accepted` are planned intent, `implemented` is evidence only when backed by code, tests or
task history, `partially-implemented` is split into live and remaining behavior, `superseded` points
at its replacement or is ignored with the uncertainty noted.

### 2. Resolve repo scope, branch policy and autonomy

Single repo, on its default branch, no `Repos` row: record `work_mode: default-branch`,
`autonomy: L1` (or the task's stricter `Autonomy`) and move on. Otherwise:

1. If `.config/repos.project.md` exists, read it and run `at repos-check`; a `Repos` row names the
   execution scope, and `at repos-check --local` validates `.local/repos.map` before another checkout
   is edited.
2. Record each repo's `Default branch`, `Integration branch` and `Work mode` in the execution log,
   and the effective autonomy (repo `Autonomy max`, task/user request, runtime limits) per the
   `agents-core:git-discipline` skill (references/autonomy-levels.md).

Branch behavior by `Work mode`: `default-branch` commits on the configured default branch (ask if
the checkout is elsewhere); `same-branch` stays put; `task-branch` uses the branch the user, task,
issue or repo `AGENTS.md` names (ask if none); `read-only` stops before writes; `ask` asks. Without
a registry, stay on the current branch if it is the default one and ask otherwise. Never create a
branch merely because this skill will commit.

Autonomy: `L0` is read-only (stop before edits); `L1` allows local edits, checks and commits; `L2`
adds push and CI repair on the allowed branch; `L3` adds draft PRs. No level authorizes merge,
deploy, release, mark-ready-for-review, history rewrite, broad connector writes, or secret exposure.
Before any later push, CI repair, PR or connector write, re-check and log that the effective level
permits it.

### 3. Protect the worktree and open the run

1. `git status --short`. Unrelated dirty changes outside the phase scope stay untouched (stage with
   explicit pathspecs); unrelated changes inside files the phase must edit: stop and ask.
2. Record the base revision (`git rev-parse --short HEAD`) in the execution log.
3. Open the run state (skip on a resumed run):

   ```bash
   at task run-state init <TASK-ID> --base <rev> --branch <branch> --work-mode <mode> --autonomy <L?> --runtime <claude|codex|inline>
   ```

   then add `mode:` and `mode_reason:` to its frontmatter. Without `agents-tasks`, write `state.md`
   by hand from [references/run-state.md](references/run-state.md).

Never use destructive cleanup to get a clean tree.

### 4. Architecture review (large mode only)

Dispatch a read-only `plan-critic` on the strongest model with the architecture brief from
[references/briefs.md](references/briefs.md) §"Architecture review". `BLOCKED`: stop and ask the user
or fix the plan. `REVISE`: update the plan/execution log, rerun or explicitly reconcile, then
proceed. Inline: a documented main-thread review labelled not independent. This review satisfies the
task convention's plan-freshness review when it covers freshness and applicability. Small mode
relies on the pre-implementation note in the task file and skips this step.

### 5. One phase at a time

For each phase whose `state.md` row is not `committed`, in order. Keep your own context to paths,
verdict blocks and the state file; open a report, diff or test log only to adjudicate a finding.

1. **Gate.** `git status --short`; run the phase's baseline checks. If a required check already
   fails, stop unless the failure is clearly unrelated and recorded as an accepted baseline.
2. **Brief.** `at task brief <TASK-ID> --phase N` writes `_runs/<TASK-ID>/phase-N/brief.md` (write
   it by hand with the same headings without `agents-tasks`). Append under `## Orchestrator notes`:
   work mode and autonomy, the **scope fence** (files and directories this phase may touch), every
   `Interface:` and `Ruling:` line from `state.md`, and any step-1 clarification. Implement only that
   phase; if the brief would need a later phase's work, update the plan first.
3. **Mark.** Row → `implementing`, `Attempt` +1, `Phase N: BASE <rev>` line.
4. **Implement.** Small mode: implement the phase yourself inside the scope fence, run its checks,
   write `phase-N/report.md` in the implementer report shape. Large mode: dispatch a fresh
   `implementer` with the prompt from [references/briefs.md](references/briefs.md) §"Implementer";
   on `NEEDS_CONTEXT` answer inside the brief's orchestrator notes and re-dispatch, on `BLOCKED`
   triage per `agents-core:subagent-protocol`. Never re-dispatch an identical prompt.
5. **Package.** `git diff <BASE> -- <scope fence> > _runs/<TASK-ID>/phase-N/diff.patch`
   (git-ignored, regenerable), then `at task size <TASK-ID> --phase N` → `phase-N/size.md`: lines per
   file before and after, code/test split, a `Flagged:` line for growth that needs a reason (hand-write
   the same table without `agents-tasks`). Row → `reviewing`. An implementer that changed nothing is
   reviewed against the run's diff since `base_rev`.
6. **Review**, read-only; each reply *is* the report — save it verbatim to its file and keep only
   the verdict block in mind. The spec judgement is the **phase checklist**; task-wide acceptance
   criteria are verified once in steps 6–7, so a reviewer that fails a phase for a later phase's
   criterion is answered with that, not with a fix round.
   - Small mode: one `reviewer`, `Stage: both`, prompt from briefs.md §"Single reviewer" →
     `review.md`; its verdict fills both `Spec` and `Quality`.
   - The quality judgement (and `Stage: both`) reads `size.md`: a flagged file whose growth no
     checklist item, finding or report line explains is an important finding; a file that grew in a
     phase meant to dedup or shrink it is critical. A `Shape:` line under the phase heading is
     checked like a checklist item.
   - Large mode, in parallel: `reviewer` `Stage: spec` → `review-spec.md`; `reviewer`
     `Stage: quality` → `review-quality.md`; `security-auditor` → `review-security.md` only when the
     phase touches a security surface (list in step 0), else `n/a`.
   Record each `Verdict` and findings count in the row.
7. **Fix loop.** While any verdict is `FAIL` or a critical finding is open: the fix loop from
   `agents-core:subagent-protocol` (cap three rounds). Write the numbered open findings to
   `phase-N/findings-R.md`; small mode fixes them yourself, large mode hands the path to the
   implementer with the round prompt; row → `fixing`; after the fix, `at task size <TASK-ID> --phase N
   --fix R` → `phase-N/size-fix-R.md` and a `Note: Phase N fix R: code net +N (<files>)` line in
   `state.md`; re-review only those findings against the fix diff and that size file
   (`phase-N/re-review-R[-<stage>].md`). A spec `FAIL` is fixed before quality findings.
   **Structural-round rule:** when rounds 1 and 2 each grew the same code file, round 3 is not a third
   guard: it uses the structural prompt from briefs.md §"Fix round" on the strongest model. If that
   round still grows the file, row → `blocked` with a note naming the shape problem, and ask the user;
   do not adjudicate it away with a `Ruling:`.
8. **Adjudicate at the cap.** Decide each still-open finding and record a `Ruling:` line in
   `state.md`; small defects you fix and rule. If every path forward is a guess, row → `blocked`,
   write what is needed, stop. In small mode a phase that hits the cap escalates the run to large
   instead (step 0).
9. **Verify and record.** Run the phase checks and related tests yourself and read the output. Tick
   the phase checkboxes, update `Updated` and `Last executed`, append a ≤ 10-line execution-log entry
   (what changed, verdicts, rulings, the `Total:`/`Flagged:` lines of `size.md`,
   `see docs/tasks_manager/_runs/<TASK-ID>/phase-N/`). Add any interface later phases depend on as an
   `Interface:` line. Run `at ledger sync`.
10. **Commit** with explicit pathspecs — the scope fence, the task/plan file and
    `docs/tasks_manager/_runs/<TASK-ID>/` — never `git add -A`:

    ```text
    <type>: <phase outcome>

    What changed:
    - <concise summary>

    Why:
    - <phase acceptance or user outcome>

    Checks:
    - <command>: <result>
    - reviews: spec <PASS|FAIL>, quality <PASS|FAIL>, security <PASS|FAIL|n/a>; rulings: <n>
    - size: +<A>/−<D>, code net <±N>, test net <±M>; flagged: <files or none>
    ```

    `<type>` is `feat`, `fix`, `chore`, `docs`, `test` or `refactor`. Failing commit hooks are fixed
    and the checks rerun; never commit a phase with failing required tests, unmet criteria, an
    unruled open finding, or a task file that does not reflect it.
11. **Close the row.** SHA, `committed`, bump `current_phase`, `updated`; then `at ledger check` and
    `at task run-state check <TASK-ID>`.

### 6. Final validation

Run the final required checks; e2e only here unless a phase required it earlier (record why when
e2e is `N/A`; do not invent a harness the plan did not ask for). Run `at task size <TASK-ID> --final`
→ `_runs/<TASK-ID>/size.md` and copy its `Total:` and `Flagged:` lines into the execution log; at
code net ≥ 600 or ≥ 15 files add `Note: PR size <…>; split candidate: <yes|no, why>` to `state.md`
so the human sees the size before a PR exists. Optionally dispatch `spec-validator`
over **all** acceptance criteria (`_runs/<TASK-ID>/validation.md`) when they are behavioral enough to
test spec-blind. Fix failures until the checks pass or a real blocker is reached; commit any fixes
or log-only updates not already in the last phase commit.

### 7. Final whole-task review

Per-phase reviews saw one diff each; this looks at the whole, with the brief from
[references/briefs.md](references/briefs.md) §"Final review", on the strongest model, read-only.
Small mode: one `reviewer` → `final-review-1.md`, with the simplicity judgement folded into its
brief, and only when there were two phases (a single phase's review already covered the task). Large
mode: two `reviewer`s (`Stage: both`) plus one `reviewer` with `Stage: simplicity` in parallel →
`final-review-1.md`, `-2.md`, `final-review-simplicity.md`, unseen by each other; all three get
`size.md`. The simplicity reviewer judges avoidable complexity only (duplicated wiring, guards
coordinating guards, one-caller abstractions, files that grew where the plan said shrink) and fails
on a flagged file with no justification or a code net over the plan's `Shape:`.

- All `PASS` with no critical finding: tick the task-wide acceptance criteria, record the result,
  finish. Non-critical findings are recorded as non-blocking.
- Any `FAIL`, critical finding or `BLOCKED`: **one** fix wave — merge the open findings into
  `_runs/<TASK-ID>/final-findings.md`, fix (small mode: yourself; large mode: one fresh implementer
  on the strongest model with the round-3 prompt, prefixed with the structural prompt when the
  simplicity review failed), commit as `fix: address execute-plan final review`, then one scoped
  re-review. If it still fails, stop and report. No second wave.

Inline: a main-thread self-review labelled "not independent", recorded and continued.

### 8. Optional squash

After the final review passes, downstream repos may squash the task's own commits into one via the
`agents-core:squash-workspace-commits` skill (per repo for multi-repo tasks; never read-only or
out-of-scope repos). Phase commits are the review and recovery boundary during execution, so never
squash early. The run directory stays until `agents-tasks:complete-task` copies its rulings into the
completion summary and removes it.

## Limits

- **One checkout per run.** A task whose `Repos` metadata spans repos is one run per repo, in the
  order the phases require.
- **Phases run in order.** No wave parallelism, so `Interface:` lines are always complete.
- **Implementers execute what they read.** An implementer with edit and Bash approval acts on the
  repository's content, including anything injected into it; the plugin hooks gate dangerous git,
  shell and secret paths, nothing else. For an untrusted repository use the worktree isolation in
  [references/runtime-claude.md](references/runtime-claude.md) and review the diff package first.

## Quality bar

- The plan/task remains the source of truth; `_runs/<TASK-ID>/state.md` is the source of truth for
  resume — a fresh session continues from the file alone.
- Your context holds paths and verdicts, not report bodies, diffs or test logs.
- Each phase is independently reviewable from its commit and its `phase-N/` directory; required
  checks are named with exact commands and run by you, not taken from a report.
- Reviews are independent or labelled as not; every unfixed finding has a `Ruling:` line.
- Unrelated work is neither staged nor committed; a squashed commit keeps the phase/review summary.
- Size is measured at every review point (`size.md`, `size-fix-R.md`, the run's `size.md`), and
  growth is either explained by a checklist item or finding, or is itself a finding.
