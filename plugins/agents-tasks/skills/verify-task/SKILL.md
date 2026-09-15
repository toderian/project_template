---
name: verify-task
description: "Check that a finished task did what its task file says: re-run its tests fresh, verify each acceptance criterion goal-backward against the code (exists, substantive, wired), detect criteria that changed during the task, and get an independent spec-blind validation plus a whole-diff review. Use when the user says \"verify task\", \"was <ID> implemented correctly\", before completing a multi-phase task, or on an already-archived task."
metadata:
  pack: task-management
---

# Verify Task

## Purpose

Answer one question with evidence: does the repository now satisfy the task file? The task file is
the spec; the commits, tests and code are the evidence; the verdict is per criterion. This skill
is report-only: it appends one execution-log entry and changes nothing else. Fixing is a separate
decision (`agents-core:execute-plan` to reopen, `agents-tasks:capture-idea` for a follow-up).

Run it before `agents-tasks:complete-task` on any task with more than one phase or an execute-plan
run, on an archived task when its outcome is in doubt, or whenever the user asks.

## Process

### 1. Resolve the task and its evidence range

Accept a task ID or path; look in `_todos/` then `_todos_archived/`. Collect:

- commit SHAs from the execution log and `docs/tasks_manager/_runs/<ID>/state.md` when present;
  otherwise `git log --grep=<ID> --oneline` (phase commits carry the ID). The range is from the
  parent of the first such commit (`<base>`) to the last (`<head>`).
- the phase checklists, acceptance criteria, `### Related tests`, and `Spec refs`
- the scope: every file touched in `<base>..<head>`

Stop and say so if no commit can be attributed to the task; verification without evidence is a
guess.

### 2. Criteria drift

Criteria that changed while the work was done are the finding no reviewer sees. Compare the task
file's history:

```bash
for c in $(git log --follow --format=%h -- <task file>); do
  echo "== $c $(git log -1 --format=%s "$c")"
  git show "$c" -- <task file> | grep -E '^[-+]- \[[ x]\] ' | sed -E 's/^[-+]- \[[ x]\] //' | sort | uniq -u
done
```

Under each commit this prints the checklist items and criteria whose **text** was added, removed
or reworded there; a commit that only ticks a box yields the same text twice and prints nothing.
The creation commit lists every item once. Classify each current criterion `unchanged | changed-during-task | added-during-task`, with the
commit that changed it, and list any criterion that was **removed** during the task. Cross-check
against the execution log: a change the log explains (a `Ruling:`, a user decision) is a decision;
one it does not explain is a finding.

### 3. Goal-backward check per criterion

For each acceptance criterion, in three steps, stopping at the first that fails:

1. **Exists** — the artifact the criterion implies (function, endpoint, file, doc, test) is in the
   tree at `<head>`.
2. **Substantive** — it is not a stub: no `TODO`/`FIXME` placeholder, no `pass`/`return None`/
   `throw new Error("not implemented")` body, no test that asserts nothing.
3. **Wired** — it is reachable: imported and called, registered, routed, or covered by a test that
   exercises it through the public interface.

Record the evidence as one `path:line` per step.

### 4. Re-run the tests

Run every `### Related tests` entry and the repo's check command fresh, and record the exact
command and exit code. Never take "passed" from the execution log. A test that cannot run is
`UNVERIFIABLE`, with the reason.

### 5. Independent passes

Dispatch read-only, in parallel, per `agents-core:subagent-protocol`:

- `spec-validator` over the acceptance criteria only (spec-blind). It may write throwaway tests
  under a scratch path outside the repo; nothing lands in the tree.
- `reviewer` with `Stage: both` over `git diff <base>..<head>`, with the task file as the spec and
  the instruction to report scope creep: files changed that no phase names.

Without subagents, do both passes yourself in a separate context break and label them
`not independent`.

### 6. Report

```markdown
## Verification — <ID> (<base>..<head>)

| # | Criterion | Drift | Exists | Substantive | Wired | Tests | Result |
|---|-----------|-------|--------|-------------|-------|-------|--------|
| 1 | … | unchanged | path:line | path:line | path:line | cmd rc=0 | MET |
| 2 | … | changed-during-task (abc1234, no ruling) | … | … | — | — | NOT MET |

Scope: <n> files changed; outside any phase: <list or none>.
Spec-validator: PASS | FAIL (<k> criteria). Reviewer: PASS | FAIL, <n> findings (C/I/M).
Removed during task: <criteria or none>.

## Verdict: PASS | GAPS | HUMAN_NEEDED
## Recommendation: accept | reopen (<criteria numbers>) | follow-up (<what>)
```

Rules: no partial results — a criterion is `MET`, `NOT MET`, or `UNVERIFIABLE`; `HUMAN_NEEDED`
when any criterion is `UNVERIFIABLE` or a drift has no recorded decision; `GAPS` when any is
`NOT MET`; `PASS` only when every criterion is `MET` and both independent passes passed. Ruled
findings from `state.md` are decisions, not gaps.

Append the verdict line, the recommendation and the table's `Result` column as one ≤ 10-line
`### <timestamp> - Verification` entry to the task's execution log (archived tasks included; the
log is append-only). Nothing else is written; do not tick or untick checkboxes.

## Quality bar

- Every `MET` has three evidence locations and a fresh test result or an explicit `no test`.
- Every drift is classified with a commit, and each unexplained one is in the report.
- Both independent passes ran, or the report says they were self-passes.
- The task file changed by exactly one execution-log entry.
