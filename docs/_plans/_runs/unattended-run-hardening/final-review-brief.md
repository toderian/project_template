Stage: both
Task description: Review the completed execution of this approved plan as a whole.
Repository: /home/vi/work/repos/project_template, branch master. Read AGENTS.md first.
Acceptance criteria:
- All plan/task acceptance criteria are satisfied (Phase 7's scenario E9, the heartbeat half of E6 and `scripts/release.sh` wait for the owner and are not defects).
- The implementation satisfies every accepted/planned spec source resolved for this task.
- Current-state claims rely only on implemented or evidence-backed partially-implemented specs, code,
  tests, or task history.
- Required checks pass and are meaningful for the changed behavior.
- Phase commits are scoped and do not include unrelated cleanup.
- No blocking regressions, security issues, or maintainability problems remain.
Context: docs/specs/2026-11-26-unattended-run-hardening-plan.md, docs/_plans/_runs/unattended-run-hardening/state.md (rulings and decisions are decisions, not defects),
git diff da43501..HEAD -- plugins scripts README.md CHANGELOG.md docs/meta (the rest of the diff is run files).
Size: docs/_plans/_runs/unattended-run-hardening/size.md (whole run; Flagged: lines need a reason, including fixture and test-ratio flags. An unjustified fixture or test-ratio flag is critical (FAIL), stricter than a code flag: bulk data growth has no logic to review. Redundant tests across layers are findings). One pass across all phases for tests duplicated between phases and fixtures duplicating each other; findings go into the one fix wave.
Pay special attention to the seams between phases built in parallel and never reviewed together: run_watch.py (phase 4) with task_report.py (phase 3), task_run.py / task_lanes.py (phases 5, 6) with the run guard and notify (phases 1, 2), and the docs of phase 7 against the code.
Consequence checklist: each item is answered in `## Evidence` as one line, or `n/a: <why>`:
1. every caller of a function whose signature, return values or errors changed;
2. the full behaviour of helpers the change starts relying on (fallthrough and default branches);
3. every newly reachable path: what it writes, publishes, logs;
4. other paths in the same flow that can break the same invariant;
5. failure paths: what is logged or persisted, before or after redaction;
6. each new check or test: name the input that makes it fail for the bug class.
A consequence that breaks an invariant or loses data or evidence is critical.
Scope fence: read-only; do not edit, stage, commit or stash files. You may run single test files (python3 scripts/tests/test_run_watch.py, test_task_run.py, test_task_report.py, bash scripts/tests/test-run-guard.sh) and `python3 scripts/build.py --check`; do not run scripts/tests/run-all.sh (it passed in the pre-commit hook of HEAD) and do not start `claude` or `codex` sessions or the live suite. Never touch ~/.local/state/agents-template/run-guard or a process you did not start.
Model hint: strongest available, highest effort.
Your reply is the review (I save it to docs/_plans/_runs/unattended-run-hardening/final-review-1.md):
the ## Status / ## Verdict / ## Findings block first (Findings: <critical>/<important>/<minor>, then numbered findings with file:line and a fix), then ## Evidence; at most 40 lines.
