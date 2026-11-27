# Post-release review: the final fix wave of supervisor packs (never reviewed)

Repo: /home/vi/work/repos/project_template (released as 1.18.0, HEAD of master). Read-only review: change nothing in the repo;
scratch work goes under /tmp/claude-1000/-home-vi-work-repos-project-template/4dde3821-15c3-414e-af23-454c15f2c77a/scratchpad/post-<your role>/.

Scope: the diff `git diff d1ca3e5 HEAD -- plugins scripts/tests` (also saved as
docs/_plans/_runs/supervisor-packs/post/diff.patch). It was written in one fix wave after four final reviews and was not
reviewed. What it claims (docs/_plans/_runs/supervisor-packs/state.md, lines starting `Final:`; CHANGELOG.md section 1.18.0):

1. `at sup land` (plugins/agents-core/lib/sup.py, `cmd_land`, `merge_result`, `squash_and_commit`): computes the merge with
   `git merge-tree --write-tree` first; a conflict outside the generated ledger files is refused before the checkout is
   touched; the untracked-content guard reads the paths the merge result adds; a branch that stops ignoring a file the hub
   holds is refused before `git add -A`; a file already in `kept/<ID>` is never replaced. Goal: no landing may delete,
   overwrite or commit a file the hub holds untracked or ignored, on any path, including a failed or repeated landing.
2. `pack_problems`: a `Repos` entry the registry does not have is a problem line.
3. sup_workers.py: `_link_local` links an existing hub file entry; `_add_dirs` adds `--add-dir` after the prompt for linked
   `local` entries on start and wake (bg and headless); `next_tasks` treats a pack with an unreadable task file as late;
   `_repos`/`_lines` refuse a non-UTF-8 map or registry by name; `_write_map` refuses on OSError; new owner-only command
   `at sup accept-tip <pack> <slug>` (guard: sup_guard.py).
4. sup_digest.py `_waits`: shows the holder of a pack repo.
5. task_lanes.SLUG is the one slug pattern.

Find defects with probes on real scratch git repos, not by reading only. Rank by harm: data loss or exposure first, then a
stuck pack with no way out, then wrong refusals of valid input, then crashes. For each finding: file:line, the exact
reproduction, what happened, what should happen. Do not report style. Say what you probed and what held.
Each test file runs alone (`python3 scripts/tests/test_sup_land.py`); the dev CLI is `python3 plugins/agents-core/lib/at.py`
(`~/.local/bin/at` is the installed copy, now also 1.18.0). Run nothing longer than two minutes.

Reply: `## Status`, `## Verdict: PASS|FAIL`, `## Findings: N (C: I: M:)`, the numbered findings, `## Evidence`.
