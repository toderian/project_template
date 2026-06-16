# Squash Workspace Commits

## Purpose

Safely compact completed workspace or task commits after validation. Use this only as a cleanup step
after the work is implemented, reviewed, and checked. The skill protects unrelated local history and
refuses pushed/shared history unless the user explicitly opts into rewriting it.

This skill is the canonical workflow for post-validation commit squashing. Other skills should route
here instead of carrying their own squash rules.

## Safety model

History cleanup is allowed only when the audit shows that the rewrite target is clean, local,
identifiable, and mechanically recoverable:

- The worktree and index are clean.
- The commits to squash are selected by task logs, commit messages, or explicit `--select` SHAs.
- No commit in the rewrite range is contained in a remote branch.
- No merge commit is in the rewrite range.
- Final validation checks are known and can be rerun after the rewrite.
- Unrelated commits are preserved in their original relative order.

If any point is uncertain, keep the commits as they are and report why. A non-squashed but correct
history is better than a clever rewrite with unclear ownership.

## Audit first

Run the bundled audit helper before planning any rewrite:

```bash
python3 playbooks/skills/productivity/squash-workspace-commits/audit-range.py \
  [--task-id TASK] [--base REF] [--head REF] [--select SHA]... [--json]
```

The helper is read-only. It reports:

- dirty worktree/index state
- candidate base/head range and selection source
- selected task commits and unrelated commits
- commits contained in remote branches
- merge commits
- changed-path overlap between selected and unrelated commits
- whether an automatic squash is allowed, and which method to use

Use `--task-id` when a task ID or task/plan file can identify the work. Use repeated `--select` when
the user names exact commits. Use `--base` when no reliable execution base or upstream range exists.

## Process

### 1. Confirm completion and validation

Do not squash while implementation is still in progress. Confirm that the task or workspace work is
complete, reviewed, and validated. Capture the exact final checks to rerun after the rewrite.

If the user asked for a squash before validation exists, run or request the relevant validation first.
The audit can prove history safety; it cannot prove product correctness.

### 2. Interpret the audit result

Proceed without another prompt only when the audit says `auto_squash.allowed: true`.

Stop and ask for explicit input when the audit reports:

- no reliable base/range
- no selected commits
- dirty worktree or index
- selected commits that are not in the candidate range
- pushed/shared commits
- merge commits in the rewrite range
- path overlap in an interleaved rewrite
- any ambiguous task ownership

For pushed/shared commits, refuse by default. Continue only if the user explicitly names the range and
says to rewrite pushed/shared history. Do not push rewritten history unless the user separately asks.

### 3. Contiguous task commits at HEAD

When the audit method is `soft-reset`, the selected commits form a contiguous suffix ending at `HEAD`.
This is the normal case.

1. Create a local backup ref first:

   ```bash
   git branch "backup/squash-workspace-commits-$(date +%Y%m%d%H%M%S)" HEAD
   ```

2. Soft reset to the audit report's `soft_reset_base`.

   ```bash
   git reset --soft <soft_reset_base>
   ```

3. Commit once with a conventional message that preserves the required details.
4. Rerun the final validation checks.
5. If validation fails, fix forward or restore from the backup ref.

### 4. Interleaved unrelated commits

When the audit method is `mixed-rewrite`, selected task commits are interleaved with unrelated commits.
Automatic rewrite is allowed only when the audit reports no selected/unrelated path overlap.

Use a scripted, non-interactive rewrite:

1. Create a local backup ref at the original `HEAD`.
2. Create a temporary branch from the candidate `base`.
3. Apply the final diff for the selected paths from original `HEAD` and create one squashed task
   commit.
4. Cherry-pick unrelated commits in their original relative order.
5. Verify `git diff <original-head>..HEAD` is empty.
6. Move the original branch to the temporary branch result.
7. Rerun the final validation checks.

Do not use this path when changed paths overlap. Path overlap means Git can no longer prove that
reordering the selected and unrelated commits preserves behavior.

### 5. Final commit message

The squashed commit body must preserve enough context for future readers to reconstruct the cleanup:

- task ID or ad-hoc summary
- original commit SHAs and subjects
- validation checks and results
- notable review or closeout notes
- any skipped squash candidates and why they were excluded

Example:

```text
feat: complete T-123 workspace cleanup

What changed:
- Squashed completed T-123 phase commits into one final commit.

Original commits:
- abc1234 feat: add parser phase
- def5678 fix: address review feedback

Validation:
- npm test: pass
- git diff --check: pass

Notes:
- Preserved unrelated commit 987abcd in original relative order.
```

## Report

Return:

- audit result and selected method, or why squash was skipped
- backup ref name if one was created
- final squashed commit SHA if squash succeeded
- validation commands and results after the rewrite
- pushed/shared-history approval status when relevant

## Quality bar

- The helper remains audit-only.
- Unrelated commits are not dropped, reordered relative to each other, or silently modified.
- Remote-contained commits are not rewritten without explicit user approval.
- The final history has one clear task/workspace commit and preserves validation evidence.
- A failed or uncertain audit leaves history unchanged.
