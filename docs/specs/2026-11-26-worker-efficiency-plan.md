# Worker efficiency before supervision: plan

Date: 2026-11-26. Status: draft, not reviewed, not started. Prerequisite of
`docs/specs/2026-11-26-supervisor-session-plan.md` (its section "Order").

## Goal

Remove four costs that every `agents-core:execute-plan` run pays today, before a supervisor starts
several such runs at once. Source: the usage profile of 2026-11-26
(`project_r1_redmesh/.no-commit/agent-usage-profile-2026-11-26/2026-11-26_complete-analysis.md`),
recommendations A1, A2, B10 and B12.

## Where we are

| Cost, as measured (dev machine, 16 days) | Cause in this repo |
|---|---|
| 76 hours in tests; about 5 full-suite runs per phase | `execute-plan` step 9 says "run the phase checks and related tests" with no bound (`skills/execute-plan/SKILL.md:264`); the fix-round brief names no check scope (`references/briefs.md`, "Fix round R") |
| Subagent Bash calls moved to the background after 180 seconds, then 19 hours of polling | no rule in the implementer or reviewer briefs for a command that runs longer |
| 72 permission denials; one sat 7.4 hours | `agents-core:unattended-run` lists permissions as a row to check (`SKILL.md:38`) and no code checks it |
| A review repeated after a rebase or an amend | `lib/peer.py` stamps `peer-reviewed/<sha>`; any new SHA for the same change loses the stamp |

Already fixed in 1.15.x, so not here: the stop on a phase summary, `agents-core:ask`, the
`complete-task` flag, heredoc handling in the git hook.

## Phases

Tests are stdlib `unittest` or the existing shell suites, run by `scripts/tests/run-all.sh`.

#### Phase 1: Test-scope ladder (A1)

- Files: `plugins/agents-core/skills/execute-plan/SKILL.md` (steps 5, 7 and 9),
  `plugins/agents-core/skills/execute-plan/references/briefs.md` (implementer, reviewer and
  fix-round briefs).
- The ladder: an implementer and a fix round run the tests of the files they touched; a reviewer
  runs a test only to settle a named doubt; step 9 runs the phase's named checks; the full suite
  runs once per task, at the final review, and once more only when a later change touches code.
- A brief carries the exact check commands of its rung, taken from the task's phase.
- Checks: the briefs name the rung; `scripts/tests/test_task_brief.py` asserts that a fix-round
  brief contains a check line and no full-suite command.

#### Phase 2: Long-command rule (A2)

- Files: `references/briefs.md`, `plugins/agents-core/agents/implementer.md`,
  `plugins/agents-core/agents/reviewer.md`, the seed `AGENTS.md`.
- The rule: a command expected to run longer than two minutes is started in the background with its
  output in a file, and the agent waits for its end once, with no polling loop; an explicit timeout
  is set on any foreground command. `TaskStop` leaves the implementer's tool list unless a use for
  it is found.
- Fact to confirm first: the documented way for a subagent to wait for a background command in the
  installed Claude Code and in Codex. The rule is written per runtime if they differ.
- Checks: `python3 scripts/build.py` regenerates the Codex agents; the briefs contain the rule.

#### Phase 3: Permission preflight (B10)

- Files: `plugins/agents-core/lib/task_run.py` or a new `lib/preflight.py`, `lib/at.py` (wiring:
  `at task preflight <TASK-ID>`), `scripts/tests/test_preflight.py`,
  `plugins/agents-core/skills/unattended-run/SKILL.md` (the Permissions row points at the command).
- What it does: collects the commands the task names in its checks and `Files:` lines and the fixed
  commands of the run (git, `at`, the test runners), and reports each one the session's settings do
  not allow or a safety hook blocks. It reads the settings files; it starts nothing.
- Fact to confirm first: which settings files and rule forms decide a permission in `auto`,
  `acceptEdits` and `dontAsk`, and what cannot be known without running the command. The command
  reports "unknown" for those, never "allowed".
- Checks: a fixture with a denied command is reported; an allowed one is not; a hook-blocked git
  command is reported; an unknown form is reported as unknown.

#### Phase 4: Peer stamp keyed on the patch (B12)

- Files: `plugins/agents-core/lib/peer.py`, `plugins/agents-core/hooks/block-dangerous-git.sh` (the
  push check), their tests.
- What changes: the stamp is keyed by the stable patch id of the reviewed range
  (`git patch-id --stable`), with the SHA kept as a second name for old stamps. A rebase or an amend
  that leaves the patch unchanged keeps the stamp; any change of content loses it.
- Checks: a rebased, unchanged commit passes the push check; a changed one does not; an old SHA
  stamp still passes.

## Order

Phases are independent. 1 and 2 are prose and go first; 3 and 4 are code. One release after all
four.

## Acceptance

- A fix round on a fixture task runs only the touched tests; the full suite runs once per task.
- No brief lets a subagent run a long command in the foreground.
- `at task preflight` names a missing permission before a run starts.
- A reviewed branch survives a rebase without a second review.
- Measured after two weeks of use with the profile's own scripts: full-suite runs per phase, and
  permission denials per run, against the numbers above.

## Out of scope

- The cost of the review loop itself (the profile's conclusion 3).
- A limit on subagents per host.
