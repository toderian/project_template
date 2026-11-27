---
name: prepare-pack
description: "Take a parent task and its open child tasks to a pack the supervisor can start: split children that mix steps or code repos, write the order, the repos, the file fences, the checks and the lab resources into each child, check the pack, and play it back to the owner. It writes task files and, through `at sup pack`, the pack record; it starts nothing. Use when the owner wants a parent's children run by a supervisor, asks to prepare, shape or check a pack, or `at sup ready --pack` reports problems."
metadata:
  pack: task-management
---

# Prepare Pack

## Purpose

A pack runs several tasks, each in its own worktree. The supervisor reads the task files and nothing else, so
whatever the owner knows about order, repos and lab use must be in them before the pack starts. This skill puts it
there. Task format: `agents-tasks:task-ledger`.

Do not use a pack when the children edit the same files, write each other's task files, or share one lab for every
step. Those run better as one session on one branch: use `agents-core:execute-plan`.

## Process

### 1. Read the parent

List the parent's open children and the order the parent states (prose, a table or `After:` lines). Read each child
file. Read `.config/repos.project.md` for the repo slugs and `.local/repos.map` for the checkouts.

### 2. Split what a pack cannot order

A pack orders whole tasks, never phases. Split a child when its phases belong to different steps of the parent's
order, or to different code repos. Hand off to `agents-tasks:add-task` for each new task, and move the phases and
criteria over. A `Blocked by` cell that names a phase (`<ID> Phase <n>`, as `RM-281 Phase 1`) is refused: name the task.

### 3. Write each child

- `Blocked by`: the tasks that must land first, by id, whole tasks only.
- `Repos` row: every repo the task changes, by slug. Every sibling repo in it needs a line in `.local/repos.map`
  and a `--branch` in the pack; the hub's own slug needs neither.
- Per phase `Files:`: the paths the phase edits. In a sibling repo write `slug:path` (`edge-node:extensions/x.py`);
  a bare path is in the task's own checkout. No `.` or `..` path segment. Two tasks that can run together may not
  share an entry.
- Per phase `Checks:`: the command that proves the phase, or a `### Related tests` section.
- `Resources:` with a duration for each lab resource, as the supervisor profile names it (`lab 20m`), or
  `Resources: none`. Write it in each child: it is not inherited from the parent.

### 4. Unattended section

Hand off once to `agents-core:unattended-run` for the parent's section (`Authorised`, `Owner only`, `Defaults`).
Children use it through the parent.

### 5. Choose the shape

- Serial (the default): one task after the previous one landed. Choose it when tasks touch the same code or each
  needs the result of the one before.
- `--parallel`: only for tasks that do not block each other and share no repo. Tasks that share a repo run one after
  another anyway, because each sibling repo has one pack branch and one worktree.
- One branch per sibling repo: `--branch <slug>=<branch>`. Each branch gets one commit per phase and is never
  pushed by the supervisor. Branch names the owner would put on a pull request.

### 6. Check

```bash
at sup pack <name> <ID>... [--parallel] [--branch <slug>=<branch>]...
at sup ready --pack <name>
```

Both need a profile: `--profile <name>` or `AGENTS_SUPERVISOR`.

`at sup ready --pack` prints `ready`, or one line per problem (`<ID>: <problem>` or `pack <name>: <problem>`) and
exits 3. `at sup pack` runs in the owner's chat or shell, not in a worker. Fix the task file the line names and
run it again. It checks every task's readiness, the order against the pack, that no blocker names a phase, that
every resource exists in the profile, that every slug is a pack repo, and that no two tasks that can run together
share a `Files:` entry. `at sup start-pack` runs the same check.

### 7. Play it back

Tell the owner, in one short list: the tasks in start order with what blocks each, the branch per sibling repo,
the lab resources and durations, what `Owner only` keeps for them, and what was split or changed. Ask for a yes.
Change what the owner corrects, check again, play back again.

### 8. Commit

Commit the task edits on the default branch (`agents-core:git-discipline`): the supervisor lands from it, and a
worker's worktree starts from it. Then tell the owner to start the pack: hand off to `agents-tasks:supervise`.

## Completion criteria

- `at sup ready --pack <name>` prints `ready`.
- The owner confirmed the playback.
- The task edits are committed on the default branch and the working tree is clean.
- No task was started and nothing was pushed.
