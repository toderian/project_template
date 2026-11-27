# Phase 4, lane B (skill and docs): implementer's reply, condensed

- plugins/agents-tasks/skills/prepare-pack/SKILL.md: new, 84 lines, no `disable-model-invocation`. Reads the parent,
  splits children that mix steps or repos (hand-off to `agents-tasks:add-task`), writes `Blocked by` (whole tasks),
  `Repos`, per-phase `Files:` (`slug:path`) and `Checks:`, `Resources:` with a duration; hand-off to
  `agents-core:unattended-run`; serial or parallel and one `--branch <slug>=<branch>` per sibling repo; `at sup pack`,
  `at sup ready --pack <name>`; playback; commit on the default branch; hand-off to `agents-tasks:supervise`.
- plugins/agents-tasks/skills/supervise/SKILL.md: pack commands of phases 1-4, checked against sup_workers.py,
  sup_digest.py, sup.py; `ready --pack` text from the brief's contract, not yet against lane A's code.
- task-ledger/references/todo-convention.md: `Files:` paragraph (`slug:path`), `Blocked by` names whole tasks for a pack.
- plugins/agents-core/seed/AGENTS.md: two routing rows. README.md: agents-tasks 26 -> 27 skills.
- test_codex_compat.py and test-codex-live.sh: 75 -> 76. build.py generated nothing new.

Output: `python3 scripts/build.py`: build: ok; `--check`: build: ok; test_codex_compat.py: Ran 9 tests OK;
test_task_brief.py: Ran 11 tests OK; `claude plugin validate plugins/agents-tasks`: Validation passed.
Open: compare the `ready --pack` wording with lane A's code. Not run: run-all.sh, test-codex-live.sh.

## Status: DONE
