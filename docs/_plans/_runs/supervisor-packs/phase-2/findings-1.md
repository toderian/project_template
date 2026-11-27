# Phase 2, fix round 1: open findings

1. [C] sup.py:234-240 — `at sup land <ID>` without `--profile`/`AGENTS_SUPERVISOR` skips the pack step
   (review-spec.md #1, review-quality.md #2, review-security.md #3). It must never land past a pack: find the
   profile whose hub is this hub and whose pack holds the task (reuse what `sup.py`/`sup_state.py` already has to
   go from hub to profile); when the task is in a pack with `branches` and no profile can be resolved, or the
   given profile is not the one that holds the task, refuse before anything changes.
2. [C] sup_workers.py:556 — `close-pack` removes a pack worktree that holds ignored files (review-quality.md #1,
   review-security.md #1). Keep the worktree and name the reason and the count; use the same notion of
   "ignored files worth keeping" as `sup.kept_ignored` (it skips caches) through one shared function, not a copy.
3. [I] sup.py:268-269 — a rerun advances tips to the current branch tip (review-quality.md #3). Required shape:
   one source for the new tip on both paths: the `<slug> <branch> <old>..<new>` lines in the body of the hub
   landing commit. After the commit exists (new or found by its `Archive:` line) read the tips from it and
   advance; never advance backwards (the new tip must be a descendant of the stored one, else leave it and say so).
4. [I] sup_digest.py:132,247,430 and sup_tick.py:364,431 — `Refused` from `_repos` escapes `status`, `done`, the
   tick and the chat (review-quality.md #4,#5, review-spec.md #3). Catch it once inside the pack-repo functions of
   sup_digest.py: `done` gets a problem line (exit 3 as for any problem), the digest gets one line naming it.
   sup_tick.py is outside the fence and must not need a change.
5. [I] sup_digest.py:186-193 — a pack with no recorded tip for a key (1.17.0) prints
   `? commit(s) over unknown, ready for PR` (review-spec.md #2). `_pack_ready_lines` lists only repos with a tip.
6. [I] sup_digest.py:191 — the registry `Integration branch` cell reaches `git rev-list` and stdout unvalidated
   (review-security.md #2). `_valid_branch` or no count; pass refs as `refs/heads/<name>`; also `_branch_exists`
   (sup_digest.py:133) with `refs/heads/` (review-security.md #5), keeping test_pack_branches_must_exist green unedited.
7. [M] sup_workers.py:547 — `close-pack` reads the map and decides per repo before it writes `closed`
   (review-quality.md #6).
8. [M] tests — add: land without a profile on a task of a pack with branches (refuses or resolves, never lands
   past); an ignored file in a pack worktree survives `close-pack`; `status` row with a real holding task id
   (review-quality.md #8, review-spec.md #4); a relative map path in `done` and `status` gives a line, not a
   traceback; the rerun after a branch moved keeps the tip of the hub commit. Shrink PackLand: drop the `kept/`
   and dirty assertions the flow test already has, keep "changes nothing" (review-quality.md #7).
9. [M] sup.py:243 — say in a code comment and the reply that a repo the task names without a new commit gets no
   range line (review-spec.md #5).

Not in this round (ruled): a worker that removes its `Repos` row before landing leaves the tips behind
(review-security.md #4): `done` and `status` catch it, nothing is lost.
