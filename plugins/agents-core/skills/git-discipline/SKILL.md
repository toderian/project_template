---
name: git-discipline
description: "Branch, commit, squash and push rules plus the autonomy ladder (L0-L3). Use when deciding where to commit, whether to branch, how to write commit messages, when squashing task commits, or when a push/force/reset is being considered."
metadata:
  source: [_base/AGENTS.md, playbooks/conventions/autonomy-levels.md]
---

# Git Discipline

## Purpose

Canonical branch, commit, and push rules for agent work, plus the autonomy ladder (L0-L3) that caps how
far an agent loop may go without asking again. Other skills point here instead of restating these rules.

## Determine repo mode

Before code edits, determine the repo mode from the user request, project-specific `AGENTS.md`, task
metadata, `.config/repos.project.md` when present, or current repo convention. `.config/repos.project.md`
is a default registry; explicit user instructions, task files, and repo-specific `AGENTS.md` override it.

If no `.config/repos.project.md` exists in a template-inherited downstream repo, default to the repo's
configured default branch (`main` or `master`). If already on a non-default branch, ask before
continuing. Do not create a feature/task branch merely because commits will be made.

**Downstream template-maintenance repos**: work directly on the default branch. Do not create feature
branches unless the user explicitly asks or host/CI policy requires it. If the session starts on a
non-default branch, ask before continuing or switching.

**Working/product repos**: work on the current/default branch unless a user instruction, task file,
issue, repo-specific `AGENTS.md`, or `.config/repos.project.md` row says `task-branch`. When
`task-branch` mode applies and no task branch is defined, ask for one, or ask whether the current branch
should be treated as the task branch. Do not create nested/subbranches unless the user explicitly asks.

`Work mode` values (`default-branch` / `same-branch` / `task-branch` / `read-only` / `ask`) and the
`Autonomy max` ceiling are recorded per repo in `.config/repos.project.md`; work mode decides *where*
work happens, autonomy decides *how far* it may go, and the strictest rule wins.

## Commit discipline

Commit after each coherent, reviewable slice: one task slice, one plan phase, one bug fix, or one
documentation batch. Do not commit every tiny edit, and do not leave a large completed task as one
uncommitted dump.

When asked to commit:

- use a concise conventional summary line with a prefix such as `feat:`, `fix:`, or `chore:`
- always include a commit body, not only a one-line summary
- structure the body as What changed / Why / Checks, each a few high-signal lines
- stage only files that belong to the completed slice; never sweep in unrelated dirty changes
- run relevant checks first, or state clearly why they could not be run

Example:

```text
feat: add retry backoff to sync client

What changed:
- Added exponential backoff with jitter to the sync client retry loop.

Why:
- Transient network errors were causing immediate retries and rate-limit bans.

Checks:
- npm test: pass
- manual retry simulation: pass
```

Task progress files are part of the work. When implementing a tracked task, update phase checkboxes,
`Updated`, `Last executed`, and the append-only execution log as work progresses.

## Push discipline

An agent may push a feature branch and open a PR (`gh pr create`) when the user asks or the effective
autonomy level allows it. The `block-dangerous-git` hook enforces the rest at every autonomy level:

- Force push (`-f`, `--force*`, `+refspec`) is always refused.
- A push that reaches a protected branch is refused. Protected by default: `main`, `master`,
  `develop`; a repo overrides the list with `git config agents.protectedBranches "main release/*"`.
  A push whose target the hook cannot resolve (bare `git push` after `cd`, `--all`, `--mirror`,
  `push.default=matching`) is refused the same way; name the remote and branch instead.
- The hook also refuses `reset --hard`, `clean -f*`, `branch -D`, `checkout .` / `restore .`, forced
  `git add`, and staging `.creds/` or `.venv/` paths.

A push to a protected branch needs two confirmations from the user:

1. Ask in chat, naming the branch and the commits. Continue only on an explicit yes for that push.
2. Run `git -c agents.allowProtectedPush=<branch> push <remote> <branch>`. The hook accepts the
   marker only for that branch, and the seed `settings.json` `ask` rule on the marker makes the harness
   prompt the user again, even in auto mode.

Never add the marker without step 1. `gh pr merge` also lands on a protected branch: ask in chat
first; the seed `ask` rule prompts again. A refusal is a guardrail: ask, do not route around it.

If asked to prepare a push-ready commit, make sure the local commit message already follows the format
above.

## Squashing

Once a task is fully implemented, validated, and reviewed, its own phase/review commits may be squashed
into a single final task commit. Route that cleanup through the `agents-core:squash-workspace-commits` skill: audit
first, squash only safely identifiable task commits, preserve the important commit-message details, and
never rewrite pushed/shared history without explicit user approval.

## Autonomy ladder

Autonomy levels cap how far an agent loop may proceed without asking again, layered on top of the
branch/work-mode rules above. Default is **L1**. See `references/autonomy-levels.md` for the full
ladder (L0 read-only inspection through L3 draft-PR validation), the explicit exclusions (merge, deploy,
release, force-push, history rewrite, mark-ready-for-review), and the resolution precedence when repo,
task, and user autonomy signals conflict.

## Quality bar

- Branch/work-mode decisions are recorded before edits, not assumed.
- Commits are conventional, sliced, and carry a What changed / Why / Checks body.
- No force-op or history rewrite is attempted, and no push reaches a protected branch without both
  user confirmations.
- Squashes go through `agents-core:squash-workspace-commits`; ad hoc history rewrites do not.
