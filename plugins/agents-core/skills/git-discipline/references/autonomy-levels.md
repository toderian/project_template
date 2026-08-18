# Autonomy Levels

## Purpose

Autonomy levels define how far an agent loop may proceed without asking again. They are a permission
ceiling layered on top of existing safety, branch, repo, task, and runtime rules. They do not replace
`Work mode`, branch resolution, sandboxing, approval policy, connector authorization, or explicit user
instructions.

Default: **L1 local dev**.

## Levels

| Level | Name | Allowed Stop Point | Examples |
|-------|------|--------------------|----------|
| L0 | Read-only inspection | Report findings only | audits, code review, research, impact analysis |
| L1 | Local development | Local edits, checks, and local commits in an approved workflow | implement a task, run tests, update docs, commit phase slices |
| L2 | Branch update and CI repair | L1 plus push/update the approved branch and repair CI for that branch | push a task branch, inspect failing checks, commit CI fixes |
| L3 | Draft PR validation | L2 plus open/update draft PRs and validate PR status | create a draft PR, update PR body, wait for checks, report status |

## Explicit Exclusions

No autonomy level in this convention authorizes:

- merge
- deploy
- release or publish packages
- mark a PR ready for review
- force-push, history rewrite, or destructive branch cleanup
- broad connector writes outside the named workflow
- writing or exposing secrets
- bypassing runtime sandbox, approval, hook, or managed-policy restrictions

These actions require explicit user instruction at the time of action, and some may still be blocked by
runtime policy or project rules.

## Level Details

### L0: Read-Only Inspection

L0 may read the repo, inspect local generated outputs, query allowed read-only tools, and produce a
report. It must not edit files, stage changes, commit, push, open PRs, modify tickets, update docs in
external systems, or write connector state.

Use L0 for audits, reviews, triage reports, research summaries, and impact assessments.

### L1: Local Development

L1 may perform local implementation inside an approved workflow:

- edit files in the allowed repo/workspace
- run relevant checks
- iterate on failures
- update local task, plan, or docs state
- create local commits when the workflow authorizes commits

L1 must stop before pushing, opening PRs, or writing to external project systems unless another rule
explicitly authorizes that specific action. Existing downstream repos remain L1 unless they opt into a
higher level.

### L2: Branch Update and CI Repair

L2 includes L1 and may update a remote branch only when all of these are true:

- the repo's effective autonomy permits L2 or higher
- the current task or user request authorizes L2 behavior
- the branch is the branch allowed by the repo's effective `Work mode`
- runtime permissions allow the required network/GitHub operations
- the push is non-destructive and does not rewrite history

L2 may inspect CI status and repair failing checks for that same approved branch. It must not open a
new PR unless L3 is effective. It must not push to a different branch just because CI would be easier
to repair there.

### L3: Draft PR Validation

L3 includes L2 and may open or update draft PRs for the approved branch. It may update a draft PR body,
link relevant task/docs context, inspect PR checks, and report PR validation status.

L3 must stop before ready-for-review, merge, deploy, release, broad reviewer assignment, or branch
protection changes. Draft PR creation is an allowed stop point, not permission to complete delivery.

## Resolution Precedence

Resolve the effective autonomy before edits or external actions.

Strictest rule wins, in this order:

1. Hard safety rules and runtime permissions: system/developer instructions, sandbox, approval policy,
   hooks, managed configuration, secret rules, and connector authorization.
2. Repo `Work mode`: determines whether writes are allowed and where work happens.
3. Branch resolution: determines the exact branch, if any, that can be edited, pushed, or used for a
   PR.
4. Repo `Autonomy max`: optional `.config/repos.project.md` ceiling. If omitted, the repo max is L1.
5. Task `Autonomy`: optional task metadata. It may lower the repo ceiling or request escalation, but
   it cannot silently exceed the repo max.

If the user directly requests a higher level for the current task, treat that as an explicit task
autonomy request. It still cannot override a stricter repo max, work mode, branch rule, safety rule, or
runtime permission. Raise the repo max deliberately in `.config/repos.project.md` when a downstream
project wants repeatable L2/L3 behavior.

## Relationship To Work Mode

`Work mode` answers **where and how work happens**:

- default branch
- same branch
- task branch
- read-only
- ask

Autonomy answers **how far the loop may proceed**:

- report only
- local edit/test/commit
- push/repair CI on the approved branch
- draft PR validation

Examples:

- `Work mode: read-only`, `Autonomy max: L3` is still read-only. Work mode is stricter.
- `Work mode: task-branch`, `Autonomy max: L2` may push only the resolved task branch.
- `Work mode: default-branch`, `Autonomy max: L1` may commit locally on the default branch but must
  stop before push.
- `Work mode: ask`, any autonomy level, requires asking before edits or branch changes.

## Metadata

Repo registry row, new optional shape:

```md
| Repo | Required | Role | Default branch | Integration branch | Work mode | Autonomy max | Areas | Notes |
|------|----------|------|----------------|--------------------|-----------|--------------|-------|-------|
| project-template | yes | Agent template | master | master | default-branch | L1 | global | Work directly on default branch |
```

The older 8-column shape without `Autonomy max` remains valid and defaults to L1.

Task metadata row, optional:

```md
| Autonomy | L0 |
```

Omit the row when the task should inherit the repo default/max. Use a lower value to make a task more
conservative than its repo. Use a higher value only when the repo max already permits it or when the
user is intentionally updating the repo ceiling as part of the same approved change.

## Logging

Before implementation, external writes, pushes, CI repair, or PR work, record:

- repo work mode
- resolved branch
- repo autonomy max
- task/user autonomy request
- effective autonomy
- any stricter runtime or safety limit that reduces the effective level

For task files, record this in `## Execution log`. For durable plans, record it in the plan execution
log. For ad hoc work, state it in the agent response before proceeding to external actions.
