# Brief, phase 7: skill text and docs (text only)

Repo: /home/vi/work/repos/project_template (agents-template marketplace), branch master, base
7df6312. Read AGENTS.md first (repo rules: edit sources only, run `python3 scripts/build.py` after
touching a source, skills <= 500 lines, full `plugin:skill` ids, descriptions name no product UI).
Plan: docs/specs/2026-11-26-unattended-run-hardening-plan.md, "Phase 7". Phases 0-6 are committed;
read `git log --stat da43501..HEAD` and docs/_plans/_runs/unattended-run-hardening/state.md (its
Decision: and Interface: lines) to learn what exists.

## Do

1. plugins/agents-core/skills/unattended-run/SKILL.md, step 3: these four questions are asked every
   time, each with a recommended default, in the `agents-core:ask` format the step already uses:
   - what to do at the review cap (recommend: park the phase, never self-rule a critical finding).
     Step 4 records the answer as an `At review cap:` line in `### Unattended run`, and whoever
     starts `at task run` passes it as `--at-review-cap park|continue`;
   - the lane cap for the night (recommend 2);
   - what to do when the model refuses or a safety classifier stops a step (recommend: route that
     phase to `at task run --harness codex`, else park);
   - what to do when another session holds a shared resource (recommend: wait up to N minutes,
     then park).
   Keep the step spec-shaped. Each answer gets a line in the `### Unattended run` section template
   of step 4.
2. README.md: the unattended-run part describes what now exists, briefly and correctly: the guard's
   status file and compaction reminder, `at notify` and its configuration, `at task report`, `at
   run-guard arm --watch` with its caps and record, `at task run` marks (`After:`, parked rows,
   `--at-review-cap`, exit code 4) and `--lanes N`, and the live suite `bash
   scripts/tests/test-unattended-live.sh [E1 ...]` (run by hand, spends tokens). Fix anything the
   earlier phases left stale; do not duplicate references/run-state.md, point at it.
3. plugins/agents-core/seed/AGENTS.md (the contract shipped downstream): only what a downstream
   agent must know: the turn-end rule lines, where the report lands
   (docs/tasks_manager/_reports/), that a watched run may be restarted. A few lines.
4. CHANGELOG.md, section "Unreleased": entries for notify, status file and compaction reminder,
   morning report, watchdog and heartbeat, driver marks, driver lanes, the live suite. Same style
   as the existing entries. Do NOT run scripts/release.sh and do not touch any version.
5. plugins/agents-core/skills/execute-plan/references/run-state.md, "Scripted driver": the
   recovery when a wave commit is rejected by the pre-commit gate (the driver exits 1 with the wave
   open; fix the gate, `git reset --hard <wave base>` as printed, then merge the parked lanes by
   hand or rerun with --retry-blocked): see the Ruling "phase 6 M2" in state.md.

## Fence

Only the five files above plus generated files written by `python3 scripts/build.py`. No code,
no tests. Do not commit, stage or stash. Do not edit docs/specs or docs/_plans.

## Checks

`python3 scripts/build.py`, then `bash scripts/tests/run-all.sh` once at the end. `wc -l` of both
SKILL.md files (<= 500).

## Reply (at most 15 lines)

What you changed per file, anything stale you corrected, anything in the code that contradicts
what the plan told you to write (do not paper over it: report it), check results, ending with:
## Status: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
