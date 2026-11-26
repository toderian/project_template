---
name: execute-parallel
description: "Execute a plan whose parts are independent as parallel lanes: each lane implements and reviews its phases in its own git worktree, lanes are merged one at a time with the checks run after each merge, and the integrated result gets its own review before the final one. Use when a task has phases marked with `After:` lines or `Execution: parallel`, when a parent task has two or more child tasks that do not block each other, or when the user asks to parallelize a task, run phases or children in parallel, or speed up a slow run."
argument-hint: "Which task, parent task or plan should run in parallel lanes?"
metadata:
  pack: core
---

# Execute Parallel

## Purpose

`agents-core:execute-plan` runs one phase at a time, so the wall-clock time of a plan is the sum of
its phases. When phases or child tasks do not depend on each other, run them at the same time and
pay only for the slowest. The price is integration: lanes were reviewed apart, so the merged result
is reviewed again as a whole.

The phase loop, briefs, reviews, fix loop, run state and commit rules are those of
`agents-core:execute-plan`. This skill decides only what runs together, where, and how it comes
back together.

Not for: a runtime without subagents (inline), a plan with fewer than two units runnable at once,
or units whose files overlap. Those go to `agents-core:execute-plan` as they are.

## Process

### 1. Build the waves

A **unit** is a phase of one task, or a whole child task of a parent.

- Phase edges: the `After:` line under the phase heading (`After: none`, `After: 1, 2`). A phase
  without one depends on the phase before it.
- Child-task edges: `Blocked by`, plus the order the parent states.
- Give each unit its scope fence (files and directories it may touch) from its checklist.

Two units share a **wave** only when all three hold: neither depends on the other; their scope
fences do not overlap; they do not need the same single-holder resource (a lab or device lock, a
port, a database, a migration number, a lockfile or other generated file). When unsure, they do not.

At most **3 lanes per wave**: more lanes burn tokens in one burst and outrun your ability to
adjudicate reviews. Extra units wait for the next wave. A child task with several phases is one lane
that runs its phases in order.

Record the result in the run state before any dispatch:
`Note: wave 1: lane A = phase 2; lane B = phase 3; lane C = RM-282`. If every wave has one lane,
stop here and use `agents-core:execute-plan`.

### 2. Open the run on the integration checkout

Run `agents-core:execute-plan` steps 1–4 (input, branch policy, worktree protection and run state,
architecture review) in the checkout and on the branch the work mode names: the **integration
checkout**. It alone holds the bookkeeping: task files, `docs/tasks_manager/_runs/`, ledgers. Lanes
never edit those, because every lane would conflict on the same state file and generated ledgers.

Done when each task in the wave has a run state and the guard is armed for all of them.

### 3. Run a wave

1. **Worktrees.** Per lane, from the integration branch's current commit (the wave base):

   ```bash
   git worktree add <worktrees dir>/<repo>-<TASK-ID>-lane-<x> -b <integration branch>-lane-<x>
   ```

   outside the checkout, where the repo keeps its worktrees. Lane branches are local and temporary;
   they are never pushed. Add `Note: lane <x>: <path>, branch <name>, base <sha>` to the run state.
2. **Dispatch all lanes in one turn**, in the background. Each implementer gets its brief by absolute
   path in the integration checkout's `_runs/<TASK-ID>/phase-N/`, writes its report there, and works
   only in its lane's worktree inside its scope fence. Model and effort as the runtime reference of
   `agents-core:execute-plan` says.
3. **Drive each lane as its own phase loop** as replies arrive: package the diff from the lane's
   base, review, fix loop, adjudicate, verify. Commit the code in the lane worktree with explicit
   pathspecs; record that SHA in the row. Keep the bookkeeping commits on the integration checkout.
   One lane waiting on a reviewer never holds another lane's next step.
4. **Park, do not stall.** A lane that blocks is parked with its worktree kept; its dependants are
   parked with it; the other lanes go on.

Done when every lane's rows are `committed` or `parked`.

### 4. Integrate the wave

In the integration checkout, one lane at a time, lowest phase or task id first:

1. `git merge --no-ff <lane branch>`. A merge, not a rebase or squash: the SHAs in the run state stay
   valid.
2. On a conflict: resolve it yourself only when both sides are additive (two entries in a list or
   registry). Otherwise abort the merge and dispatch a fresh implementer in that lane to rebuild its
   change on the integration branch's current commit; its diff is reviewed again.
3. Run the full checks after **each** merge, so a failure names its lane. Fix it in that lane's
   scope before the next merge.
4. `Note: lane <x> merged at <sha>`.

Then review the wave: `git diff <wave base>..HEAD` goes to two independent reviewers with the
question the lane reviews could not answer: do the lanes fit together? Interfaces one lane defines
and another uses, the same helper written twice, every conflict resolution, behaviour that only
exists once both are present. One fix wave, as at the final review of `agents-core:execute-plan`.
Record the `Interface:` lines the next wave needs; they are complete only at this point.

Remove each merged lane (`git worktree remove`, `git branch -d`), then start the next wave from the
new integration commit.

### 5. Finish

Final validation, the whole-task review and closeout are `agents-core:execute-plan` steps 6–8, run
on the integration branch. For a parent task, each child closes out on its own, then the parent.

## Limits

- Lanes in different repositories are independent by construction: one integration checkout per
  repo, the 3-lane cap across all of them.
- A wave costs roughly its lane count in tokens at once. On a tight budget, lower the cap.
- A resource only one holder may use (a lab, a device) makes its units serial however the files fall.

## Quality bar

- Every unit in a wave passed all three independence tests, and the waves are in the run state.
- Bookkeeping exists only in the integration checkout; lane commits hold code only.
- The checks ran after each merge; the integrated diff of every wave was reviewed.
- No lane worktree or branch outlives its merge, except a parked lane's, which is noted.
