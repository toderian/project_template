# Phase 1, fix round 1: open findings

1. [C] sup_workers.py:619-643 — a failed restart loses `sibling_base` (review-quality.md #1). Required shape, not a
   guard: delete the per-row `sibling_base`. Record the tip per pack repo once in the pack record, as
   `pack["tips"] = {slug: sha}`, written by `start-pack` when it creates or attaches the worktree and never
   overwritten by a second `start-pack`. Tasks on one repo run one after another, so a task's base is the pack's
   tip for that repo; Phase 2 advances it at landing. `sup_state.py` gives `tips` the default `{}`.
2. [I] sup_workers.py:380-384 — the registry `Integration branch` cell reaches git unvalidated (review-quality.md #2,
   review-security.md #1). Run it through `_valid_branch`; refuse by name.
3. [I] sup_workers.py:378 — `--branch slug=<branch>` may name the repo's default or integration branch
   (review-security.md #2). Refuse when it equals either registry cell of that repo (`_repos` must return both).
4. [I] phase-1/report.md is missing (review-spec.md #1, review-quality.md #3). Write it per the brief's report
   contract, Test plan first, covering round 0 and this round.
5. [M] sup_workers.py:263 — `_task_repos` is a second parser (review-spec.md #2, review-quality.md #5). Use the
   reader `sup.py` already uses for task metadata (`task_brief.parse_task`, see sup.py:314-320) or one shared
   helper; a cell in backticks must give the slug.
6. [M] sup_workers.py:484 — `at sup start-worker <ID>` by hand ignores the one-task-per-repo rule
   (review-quality.md #4). `_refusal` (or the one place both paths share) refuses, naming the task that holds the repo.
7. [M] sup_workers.py:355 — `_git` lets `TimeoutExpired`/`OSError` escape as a traceback (review-quality.md #7). Refuse with exit 3.
8. [M] sup_workers.py:414 — the same slug twice in `--branch` is refused (review-quality.md #8).
9. [M] sup_workers.py:255 — a map path that is not absolute is refused by name (review-security.md #3).
10. [M] sup_workers.py:596 — refuse to write the map when `.local` or `.local/repos.map` in the task worktree is a
    symbolic link (review-security.md #4).
11. [M] sup_workers.py:443-447 — under the lock, refuse `start-pack` when the pack's `branches` differ from the ones
    the git work used (review-quality.md #9).
12. [M] tests — add: attach to an existing branch; integration branch `N/A` falls back to the checked-out branch;
    `tips` survives a second `start-pack` and a failed worker start. Remove the duplicate assert on the prompt
    constant at test_sup_workers.py:404 (review-quality.md #6, review-spec.md #3).

Not in this round (ruled by the orchestrator): `REPEATABLE` being global in sup_guard.py (review-security.md #5).
