# Run state: `docs/tasks_manager/_runs/<TASK-ID>/`

The run directory is the orchestrator's memory. It is committed with each phase commit (except
`diff.patch`, which the seed `.gitignore` block ignores because it is regenerable), so any session on
any machine can resume. `agents-tasks:complete-task` copies its `Ruling:` lines into the completion
summary and removes the directory.

## Layout

```text
docs/tasks_manager/_runs/<TASK-ID>/
  state.md                 resume map; rewritten by the orchestrator only; keep under 60 lines
  lock                     `<pid> <host> <started>` while `at task run` (or an orchestrator that
                           chooses to) holds the run; git-ignored
  phase-N/brief.md         at task brief <TASK-ID> --phase N, plus the orchestrator notes you append
  phase-N/report.md        implementer's full report (its chat reply is ≤ 15 lines)
  phase-N/diff.patch       git diff <BASE> -- <scope fence>; the reviewers' input (git-ignored)
  phase-N/review.md        small mode: the single reviewer's reply, Stage: both (you save it)
  phase-N/review-spec.md   large mode: reviewer reply, Stage: spec (reviewers are read-only: you save the reply)
  phase-N/review-quality.md large mode: reviewer reply, Stage: quality
  phase-N/review-security.md security-auditor reply, only when the phase touched a security surface
  phase-N/findings-R.md    numbered open findings handed to fix round R
  phase-N/re-review-R-<stage>.md scoped re-review reply after fix round R
  validation.md            optional spec-validator run over all acceptance criteria (step 6)
  final-review-1.md, -2.md the whole-task reviews (step 7; only -1 in small mode); final-findings.md if a fix wave ran
```

## `state.md` format

Written by `at task run-state init`, validated by `at task run-state check`, edited by hand between:

```markdown
---
task: EGM-012
task_file: docs/tasks_manager/_todos/EGM-012-F_example.md
runtime: claude | codex | inline
mode: small | large
mode_reason: 3 phases
base_rev: a1b2c3d
branch: master
work_mode: default-branch | same-branch | task-branch | read-only | ask
autonomy: L0 | L1 | L2 | L3
current_phase: 2
updated: 2026-09-15T14:02:00
---
# Run ledger — EGM-012

| Phase | Status | Attempt | Spec | Quality | Security | Open | Commit | Agent |
|---|---|---|---|---|---|---|---|---|
| 1 | committed | 1 | PASS | PASS | n/a | 0 | 9f8e7d6 | — |
| 2 | fixing | 2 | FAIL | PASS | PASS | 1 | — | agent-3f1c |

Phase 1: BASE a1b2c3d; complete (commit 9f8e7d6, review clean)
Phase 2: BASE 9f8e7d6; fix round 1/3 (2 addressed, 1 open: validator ignores empty payload)
Ruling: empty-payload check — accepted as-is, phase 3 owns payload validation — cost if wrong: one extra 400 path
Interface: SessionValidator.validate(token) -> Result[Session, SessionError]  (phase 1, for later phases)
Note: e2e is N/A for this repo (no browser harness); recorded in the task file
```

Rules the validator enforces:

- Frontmatter keys: `task`, `task_file`, `runtime`, `base_rev`, `branch`, `work_mode`, `autonomy`,
  `current_phase`, `updated`. `runtime` is `claude`, `codex` or `inline`. `mode` (`small` | `large`)
  and `mode_reason` are written by the orchestrator; a file without them is a large run.
- One table row per `#### Phase` heading in the task file, numbered like the ledger's `n/m`.
- `Status` is one of `pending | implementing | reviewing | fixing | committed | blocked | parked`.
- `Spec`, `Quality`, `Security` cells are `—` (not run yet), `n/a`, `PASS` or `FAIL`. In small mode the
  single reviewer's verdict fills both `Spec` and `Quality`.
- A `committed` row has a SHA in `Commit`, and every SHA must exist in the repository.
- Free lines after the table start with `Phase N:`, `Ruling:`, `Interface:` or `Note:`. Nothing else.
- `Agent` holds a subagent id when the runtime can resume by id (Claude Code); otherwise `—`.

`Open` is the count of findings not yet fixed or ruled. `Attempt` counts implementer dispatches for
the phase including fix rounds.

## Resume

A resumed run starts from the file, not from memory:

1. Read `state.md`. Run `at task run-state check <TASK-ID>`; fix the file before continuing if it fails.
2. For every `committed` row, confirm the SHA with `git cat-file -e <sha>^{commit}` and that the phase
   checkboxes in the task file are ticked. A missing commit means the branch moved: stop and ask.
3. Re-read every `Ruling:` and `Interface:` line; they go into the next brief's orchestrator notes.
4. If `lock` exists and names a live process on this host, another run is in progress: stop.
   A dead pid is a stale lock from an aborted run; delete it and continue.
5. `git status --short`. Uncommitted changes inside a phase's scope fence mean an implementer was
   interrupted: package them as `diff.patch` and go straight to review for that phase, or discard them
   only with the user's consent.
6. Continue at the first row that is not `committed`:
   - `pending` → step 5 from the brief.
   - `implementing` → the brief exists; dispatch a fresh implementer (a stale `Agent` id from another
     session cannot be resumed; leave it and continue).
   - `reviewing` / `fixing` → regenerate `diff.patch` from `BASE` and rerun the reviews or the pending
     fix round; the `findings-R.md` files say where the loop stopped.
   - `blocked` / `parked` → a human decision is recorded as missing; ask before continuing.
7. Set `runtime:` to the runtime you detected now — it may differ from the session that started the run.

## Without agents-tasks

For `docs/_plans/<slug>.md` or a pasted plan in a repo without the task ledger, keep the same loop
with the run directory at `docs/_plans/_runs/<slug>/` and write the files by hand:

- `brief.md`: the phase heading and body, the plan's acceptance criteria and checks, the same
  `## Orchestrator notes` and `## Report contract` sections `at task brief` would emit.
- `state.md`: the format above, `task_file` pointing at the plan.
- Phase numbering follows the plan's `## Phase N:` / `#### Phase N:` headings in order.

`at ledger check` does not know this directory; remove it by hand when the plan is done.

## Scripted driver

`at task run <TASK-ID> [--harness claude|codex] [--mode small|large|auto] [--phase N] [--check CMD]... [--security]
[--model M] [--strong-model M] [--max-rounds 3] [--timeout 1800] [--budget-usd 5] [--no-commit]
[--no-final-review] [--retry-blocked] [--force-unlock] [--dry-run]` executes this loop without an orchestrating session: it writes the same files, one
process per dispatch, and commits each phase (`feat: <ID> phase N — <title>`), leaving `state.md`
dirty until the next phase's commit sweeps it in and committing the last one as
`chore: <ID> run state`. Differences from the skill:

- `--mode auto` (default) picks large on ≥ 3 phases, `--security`, a `Repos` row, a `### Design`
  section or `Execution: orchestrated`; it cannot count files. Small mode still dispatches an
  implementer (the driver has no "self") but runs one `Stage: both` reviewer per phase and one
  final reviewer (none for a single phase). A run never de-escalates from large.
- The clean-tree gate is strict: any change outside `_runs/` stops the run.
- The scope fence is "only what the phase requires"; the script cannot infer file lists.
- Security review runs on every phase or none (`--security`); checks come from `--check`, and on
  Claude the reviewers may run exactly those commands (`Bash(<cmd>)` allow rules) and nothing else.
- At the fix-loop cap the row becomes `blocked` with the open findings noted; there is no
  adjudication. Add `Ruling:` lines (or fix by hand) and rerun — with `--retry-blocked` if you leave
  the row `blocked`, or plainly after setting it back to `pending`.
- `driver.log` in the run directory records every process, its stderr and (Claude) its cost.
- Every dispatch is bounded: `--timeout` kills a silent process and marks the row `blocked`;
  `--budget-usd` is passed to `claude -p` as `--max-budget-usd` (Codex has no equivalent — the
  timeout is the only cap there). A reply without a status block is asked for once more, like the
  `SubagentStop` hook does for subagents, then the row is `blocked`.
- One run at a time: the `lock` file refuses a second driver while the first is alive.
- After each commit it runs `at task run-state check` and `at ledger check`; a failure blocks the next phase.
