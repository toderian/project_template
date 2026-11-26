Task description: Review this approved implementation plan before execution.
Plan: docs/specs/2026-11-26-unattended-run-hardening-plan.md (repo: agents-template, a plugin marketplace of skills, hooks and the `at` CLI for Claude Code and Codex; tests: `bash scripts/tests/run-all.sh`).
Already built and committed (54ad321): plugins/agents-core/hooks/run-guard.sh, `at run-guard` in plugins/agents-core/lib/at.py, skills agents-core:unattended-run, execute-parallel, ask.
Acceptance criteria:
- The plan fits the existing architecture and local patterns (AGENTS.md: bash + python3 stdlib + jq only, no vendored code, generated files via scripts/build.py).
- Phase boundaries are independently committable and do not hide cross-phase dependencies; the `After:` lines and the Order section are correct (which phases really share files).
- Test strategy (unit, fixture, the live end-to-end scenarios E1-E9) is sufficient for the stated acceptance criteria.
- Risks are identified: a watchdog that restarts sessions unattended, a notify command run from a hook, headless resume, merge logic in the scripted driver.
Scope fence: read-only; do not edit files.
Context files: the plan; plugins/agents-core/hooks/run-guard.sh; plugins/agents-core/hooks/hooks.json; plugins/agents-core/lib/at.py (cmd_run_guard); plugins/agents-core/lib/task_run.py; plugins/agents-core/skills/execute-plan/SKILL.md and references/run-state.md; plugins/agents-core/skills/unattended-run/SKILL.md; plugins/agents-core/skills/execute-parallel/SKILL.md; scripts/tests/run-all.sh; scripts/tests/test-codex-live.sh.
Model hint: strongest available, highest effort.
Your reply is the review; at most 40 lines ending in:
## Status: DONE | DONE_WITH_CONCERNS | BLOCKED
## Architecture verdict: PROCEED | REVISE | BLOCKED
## Blocking findings: <count>, one line each
## Required plan changes: <one line each>
