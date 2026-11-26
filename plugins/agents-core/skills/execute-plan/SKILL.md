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
phase yourself and two independent reviewers check it. In **large** mode you are a thin orchestrator: you
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
- Each phase passed an independent review (two reviewers in small mode, `Stage: both` and the second
  reviewer brief; separate spec
  and quality reviewers, plus security when the phase touched a security surface, in large mode),
  or every open finding carries a `Ruling:` line.
- The final whole-task review reports no blocking or acceptance-failing findings.
- Residual concerns are recorded as non-blocking.
- Every decision taken without the owner has a `Decision:` line in `state.md`.

If a phase does not converge within the fix-loop cap, or the final review does not converge in one
fix wave, stop and report the remaining issues instead of looping.

## Run to the end

A run is finished when every row is `committed` and closeout is done, or when every row left is
`parked` or `blocked`. A committed phase, a written summary and a compacted context are not stopping
points: report progress in a line and start the next row in the same turn.

- Step 3 arms the run guard. From then on a turn may end mid-run only when the last message carries,
  on a line of its own, `Run: WAITING <the background job or subagent that will report back>` or
  `Run: BLOCKED <what only the owner can decide>`; a Stop hook sends anything else back to the first
  open row. `WAITING` needs something running now that will wake the session. `BLOCKED` is for when
  no open row can proceed without the owner.
- A task marked `Execution: unattended` is decided by `agents-core:unattended-run`: inside the scope
  the owner authorised you choose and record a `Decision:` line, outside it you park the row and
  continue with what does not depend on it.
- A question to the owner goes through `agents-core:ask`, never as a bare sentence.

## Process

### 0. Pick the rung

| Rung | When | What runs |
|---|---|---|
| trivial | a one-sentence diff, not a tracked task | not this skill: edit, test, commit (`agents-core:tdd`) |
| **small** | ≤ 2 phases, scope fence ≤ ~10 files, no large trigger | you implement each phase; two `reviewer`s per phase (`Stage: both` + second reviewer); two final reviewers plus the peer |
| **large** | any large trigger | thin orchestrator: `plan-critic` architecture review, fresh `implementer` per phase, parallel spec + quality reviewers, conditional `security-auditor`, two final reviewers |
| parallel | phases carry `After:` lines or the task says `Execution: parallel`, or a parent task has ≥ 2 children that do not block each other | `agents-core:execute-parallel`: lanes in worktrees, each lane on its own rung, then integration |
| program | too big for one task, way ahead unclear | `agents-tasks:wayfinder`; each resulting task runs its own rung |

**Large triggers** — any one is enough; record which in `state.md` as `mode_reason:`:

- ≥ 3 phases, or a phase whose scope fence exceeds ~10 files;
- a security surface (auth or sessions, input parsing or deserialization, subprocess/shell/file-path
  handling, network or HTTP, secrets/config/env, permissions or ACLs, SQL or query building, crypto,
  CI or hook configuration, new dependencies, error handling and logging of user or target data,
  persistence of reports or evidence, redaction), a data migration, a public interface or contract, or
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

   then add `mode:` and `mode_reason:` to its frontmatter. When the code diff lives in another checkout
   than the one holding `_runs/` (the task's `Repos` row, paths in `.local/repos.map`), add
   `--code-repo <path>` to `init` (or `code_repo:` to the frontmatter): step 7 and the peer gate use it. Without `agents-tasks`, write `state.md`
   by hand from [references/run-state.md](references/run-state.md).
4. Arm the run guard, on a resumed run too: `at run-guard arm <TASK-ID>` with every task of an
   authorized chain (`at run-guard arm RM-280 RM-282 RM-276`), or the path of `state.md` for a plan
   without the task ledger. Exit 3 means this harness has no hook for it: keep §"Run to the end" by
   hand. The guard ends itself when the tasks are archived; `at run-guard disarm` is the owner's.
   When the task's `### Unattended run` section says `Watch: on`, arm with the watchdog instead:
   `at run-guard arm --watch --budget-usd <its watch budget> --max-resumes <its restarts> <TASK-ID>`,
   plus `--allow-bypass` only when that section has an `allow bypass` line. A detached watcher then
   restarts this session headless if its process dies ([references/run-state.md](references/run-state.md)).
   A re-arm (a resumed run) keeps a running watcher with its caps; a new watcher continues the restart
   count, and its caps can only lower the recorded ones. To change the caps of a live watcher,
   `at run-guard disarm`, then `arm --watch`, which starts a new count. `arm --watch` prints the restarts left.
5. Heartbeat, for a task marked `unattended` and only where the harness has a scheduler (a recurring
   wakeup in an interactive session): schedule one, every 30 minutes unless the task says otherwise,
   with the prompt `run guard check: if the job you are waiting for is still
   running, reply Run: WAITING <job>; if it died or nothing is running, resume from state.md`. It
   catches a job that never reports back and quota that returned. A scheduled wakeup dies with the
   process and never fires under `claude -p`: a headless run has no heartbeat and relies on the
   watchdog. Cancel the wakeup at closeout (step 8).

Never use destructive cleanup to get a clean tree.

### 4. Architecture review (large mode only)

Dispatch a read-only `plan-critic` on the strongest model with the architecture brief from
[references/briefs.md](references/briefs.md) §"Architecture review". `BLOCKED`: stop and ask the user
or fix the plan. `REVISE`: update the plan/execution log, rerun or explicitly reconcile, then
proceed. Inline: a documented main-thread review labelled not independent. This review satisfies the
task convention's plan-freshness review when it covers freshness and applicability. Small mode
relies on the pre-implementation note in the task file and skips this step.

Peer check: in parallel, the same brief goes to `at peer run --role plan-critic` →
`architecture-review-peer.md`, per `agents-core:subagent-protocol` §"Peer check".

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
   write `phase-N/report.md` in the implementer report shape, `## Test plan` first. Large mode: dispatch a fresh
   `implementer` with the prompt from [references/briefs.md](references/briefs.md) §"Implementer";
   on `NEEDS_CONTEXT` answer inside the brief's orchestrator notes and re-dispatch, on `BLOCKED`
   triage per `agents-core:subagent-protocol`. Never re-dispatch an identical prompt.
5. **Package.** `git diff <BASE> -- <scope fence> > _runs/<TASK-ID>/phase-N/diff.patch`
   (git-ignored, regenerable), then `at task size <TASK-ID> --phase N` → `phase-N/size.md`: lines per
   file before and after, code/test/fixture split, a `Flagged:` line for growth that needs a reason (hand-write
   the same table without `agents-tasks`). Row → `reviewing`. An implementer that changed nothing is
   reviewed against the run's diff since `base_rev`.
6. **Review**, read-only; each reply *is* the report — save it verbatim to its file and keep only
   the verdict block in mind. The spec judgement is the **phase checklist**; task-wide acceptance
   criteria are verified once in steps 6–7, so a reviewer that fails a phase for a later phase's
   criterion is answered with that, not with a fix round.
   - Small mode, in parallel: `reviewer` `Stage: both`, prompt from briefs.md §"Single reviewer" →
     `review.md`, and `reviewer` with briefs.md §"Second reviewer" (tests and failure paths) →
     `review-2.md`. Both must pass; together they fill `Spec` and `Quality`. Every review round has at
     least two independent reviewers, per `agents-core:subagent-protocol` §"Review round".
   - The quality judgement (and `Stage: both`) reads `size.md`: a flagged file whose growth no
     checklist item, finding or report line explains is an important finding; an unjustified fixture or test-ratio flag is critical (stricter than a
     code flag: bulk data growth has no logic to review); a file that grew in a
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
   `state.md`; small defects you fix and rule. A finding whose acceptance loses data or evidence
   needs the owner's ruling in chat (`agents-core:subagent-protocol` §"Fix loop"), not yours. If every path forward is a guess, row → `blocked`,
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
Small mode: two `reviewer`s in parallel, unseen by each other: reviewer 1 → `final-review-1.md`, with
the simplicity judgement folded into its brief, and the unanchored reviewer 2 (briefs.md §"Final
review 2") → `final-review-2.md`, plus the peer (below). Large
mode: two `reviewer`s (`Stage: both`) plus one `reviewer` with `Stage: simplicity` in parallel →
`final-review-1.md`, `-2.md`, `final-review-simplicity.md`, unseen by each other. Reviewer 1 and the
simplicity reviewer get `size.md`; reviewer 2 is **unanchored**: the brief from briefs.md §"Final
review 2" holds only the goal sentence, the diff range and the consequence checklist, no plan,
design, `Ruling:` lines or state, so it cannot conform to a decision that was wrong. The simplicity reviewer judges avoidable complexity only (duplicated wiring, guards
coordinating guards, one-caller abstractions, files that grew where the plan said shrink) and fails
on a flagged file with no justification or a code net over the plan's `Shape:`. Large mode also
sends the final-review brief to `at peer run --role reviewer` → `final-review-peer.md`, per
`agents-core:subagent-protocol` §"Peer check"; its confirmed findings count like a reviewer's.

**Peer at the final review of every rung that ends with code commits** (small mode too), not only
large mode. Run it with cwd = the checkout that holds the code diff, because `at peer` is enabled and
`--required` is set per checkout: a peer enabled only where `_runs/` lives never reviews the code. If it
exits 3 and that checkout is `required`, the review is BLOCKED: fix the setup, do not skip it. Before
closeout run `at task run-state check <TASK-ID> --final`: it fails when phases are committed,
`final-review-peer.md` is missing and the `code_repo` checkout requires the peer.

- All `PASS` with no critical finding: tick the task-wide acceptance criteria, record the result,
  proceed to closeout. Non-critical findings are recorded as non-blocking.
- Any `FAIL`, critical finding or `BLOCKED`: **one** fix wave — merge the open findings into
  `_runs/<TASK-ID>/final-findings.md`, fix (small mode: yourself; large mode: one fresh implementer
  on the strongest model with the round-3 prompt, prefixed with the structural prompt when the
  simplicity review failed), commit as `fix: address execute-plan final review`, then one scoped
  re-review. If it still fails, stop and report. No second wave.

Inline: a main-thread self-review labelled "not independent", recorded and continued.

### 8. Close out the task

After the final review passes, hand a tracked task to `agents-tasks:complete-task` as part of the
authorized work, without waiting for a separate closure request. Only close when the whole task
scope is complete, including other repositories when applicable. Continue an already-authorized
task chain after closeout succeeds; otherwise report its blocker and keep dependent tasks waiting.

For a standalone plan without a task ledger, record its completed acceptance evidence and commit
the final plan update. Downstream repos may then use `agents-core:squash-workspace-commits` for
optional history cleanup. Phase commits remain the review and recovery boundary during execution;
never squash early or remove run evidence before closeout consumes it.

## Limits

- **One checkout per run.** A task whose `Repos` metadata spans repos is one run per repo, in the
  order the phases require.
- **Phases run in order here.** `Interface:` lines are then always complete. Independent phases or
  child tasks run as waves under `agents-core:execute-parallel`.
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
