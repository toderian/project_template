# Agent Loop Recipes

## Purpose

Loop recipes are compact operating specs for repeatable agent loops. They describe the minimum
autonomy, workspace isolation, allowed stop point, and human gates before a loop runs.

Use these recipes when turning a recurring workflow into an automation, scheduled check, subagent
pattern, CI-repair loop, or draft-PR loop. Keep the first version small, reversible, and easy to audit.

## Recipe Fields

| Field | Meaning |
|-------|---------|
| Recipe | Short stable name for the loop. |
| Minimum autonomy | Lowest autonomy level required to complete the loop's allowed stop point. |
| Required work mode | Repo `Work mode` values that are compatible with the recipe. |
| Workspace mode | `current-checkout`, `single-worktree`, `one-worktree-per-agent`, or `read-only`. |
| Allowed stop point | The furthest action the loop may take before reporting or asking. |
| Must ask before | Actions that always require fresh human approval. |

Autonomy levels come from `playbooks/conventions/autonomy-levels.md`. Work mode still controls where
work happens. The strictest rule wins.

## Examples

| Recipe | Minimum autonomy | Required work mode | Workspace mode | Allowed stop point | Must ask before |
|--------|------------------|--------------------|----------------|--------------------|-----------------|
| L0 audit | L0 | `read-only`, `same-branch`, `default-branch`, `task-branch`, `ask` | `read-only` | Report findings with file/line evidence | edits, staging, commits, connector writes |
| L0 long-task planning | L0 | `read-only`, `same-branch`, `default-branch`, `task-branch`, `ask` | `read-only` | Next-slice brief printed or recorded from task/workbook state | edits, staging, commits, provider calls, connector writes |
| L1 local implementation | L1 | `same-branch`, `default-branch`, `task-branch` | `current-checkout` or `single-worktree` | Local commit after checks pass | push, PR, merge, deploy, force-push |
| L1 workbook-backed execution | L1 | `same-branch`, `default-branch`, `task-branch` | `current-checkout` or `single-worktree` | One workbook-backed task slice completed, checked, logged, and locally committed | push, PR, merge, deploy, force-push, new runtime dependency |
| L2 CI repair | L2 | `same-branch`, `default-branch`, `task-branch` | `single-worktree` | Push fix commits to the approved branch and report CI status | switching branch, opening PR, force-push, non-CI scope |
| L3 draft PR validation | L3 | `same-branch`, `default-branch`, `task-branch` | `single-worktree` | Draft PR opened or updated, PR checks inspected, status reported | ready-for-review, merge, deploy, release, force-push |

## Long-Task Planning Loop

The L0 long-task planning loop is read-only. It is for resuming a long task without guessing from the
conversation transcript.

```text
intake -> current-state review -> classify task -> select next phase -> gather workbook commands
       -> plan next slice -> verify plan -> critique risks -> checkpoint recommendation
```

Use `workbooks/prompt-orchestration-long-task/scripts/plan_next_slice.py` when the seeded workbook has
been adopted downstream. The script may read a task file and a related workbook README, then print a
brief. It must not call providers, run workbook commands, read `.creds/`, write files, or change Git
state.

## Workbook-Backed Execution Loop

The L1 workbook-backed execution loop starts only after the planning loop has identified a small,
reviewable next slice.

```text
baseline check -> implement one slice -> run workbook/task checks -> verify acceptance criteria
              -> critique failure modes -> update task execution log -> local commit
```

This loop uses the current checkout or one worktree for the approved branch. It may run workbook
commands and make local edits within the resolved work mode, but it still stops before push, PR,
merge, deploy, force-push, connector writes, or adding a new runtime dependency unless separately
approved by repo policy and the user.

## Worktree Isolation

Use worktrees when a loop may run in parallel with another loop, with a human session, or with
subagents that own disjoint slices. Worktrees reduce mechanical file collisions; they do not remove
integration, branch-policy, or review risk.

Recommended defaults:

- One agent editing one narrow slice can use the current checkout when the worktree is clean and no
  parallel work is active.
- Parallel implementation agents should use one worktree per agent and explicit file ownership.
- Read-only audit loops do not need worktrees unless the runtime requires isolated scratch state.
- L2/L3 loops should use a single resolved branch/worktree for the branch they are allowed to update.

Local worktree directories named `.worktrees/` and `worktrees/` are ignored by this template. Do not
commit generated worktree checkouts. If a downstream project intentionally commits a directory named
`worktrees/`, override the ignore rule locally and document why.

## Stop Rules

Every recipe must name a stop point that can be checked. Examples:

- "report findings"
- "local commit created and checks passed"
- "approved branch pushed and CI status reported"
- "draft PR opened and PR checks inspected"

Avoid open-ended stop points such as "finish the feature" unless the task itself decomposes the loop
into phase-level checks and commits.

## Memory

Record loop state outside the active conversation:

- task execution log
- `docs/_plans/<slug>.md`
- `AGENT_PROGRESS.md` for long-running local loops
- PR body or comment for PR-scoped loops
- `docs/resources/_reports/<workflow>/` for rerunnable audits

The state file should record the last observed inputs, the action taken, checks run, stop point reached,
and remaining human decisions.
