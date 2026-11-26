# Worker efficiency before supervision: plan

Date: 2026-11-26. Status: draft, not reviewed, not started. Prerequisite of
`docs/specs/2026-11-26-supervisor-session-plan.md` (its section "Order").

## Goal

Remove three costs that every `agents-core:execute-plan` run pays today, before a supervisor starts
several such runs at once. Source: the usage profile of 2026-11-26
(`project_r1_redmesh/.no-commit/agent-usage-profile-2026-11-26/2026-11-26_complete-analysis.md`),
recommendations A1, A2 and B12 (B10 moved, see "Moved out").

## Where we are

| Cost, as measured (dev machine, 16 days) | Cause in this repo |
|---|---|
| 76 hours in tests; about 5 full-suite runs per phase | `execute-plan` step 9 says "run the phase checks and related tests" with no bound (`skills/execute-plan/SKILL.md:264`); the fix-round brief names no check scope (`references/briefs.md`, "Fix round R") |
| Subagent Bash calls moved to the background after 180 seconds, then 19 hours of polling | no rule in the implementer or reviewer briefs for a command that runs longer |
| A review repeated after a rebase or an amend | `lib/peer.py` stamps `peer-reviewed/<sha>`; any new SHA for the same change loses the stamp |

Already fixed in 1.15.x, so not here: the stop on a phase summary, `agents-core:ask`, the
`complete-task` flag, heredoc handling in the git hook.

## Phases

Tests are stdlib `unittest` or the existing shell suites, run by `scripts/tests/run-all.sh`.
Revised after one `agents-core:plan-critic` round (REVISE, composite 2.2); the revision is not
reviewed again.

#### Phase 1: Test-scope ladder (A1)

- Files: `plugins/agents-core/skills/execute-plan/SKILL.md`,
  `plugins/agents-core/skills/execute-plan/references/briefs.md`, `plugins/agents-core/lib/task_run.py`
  (its copy of the implementer and fix-round prompts), `scripts/tests/test_task_run.py`. Ceiling:
  40 changed lines of prose, 15 of code.
- The ladder: an implementer and a fix round run only the tests of the files they touched; a
  reviewer runs a test only to settle a named doubt (already in the briefs); the orchestrator runs
  the phase's named checks and the full suite once per phase, before the commit, and not again in
  that phase unless a fix changed code after it. The profile found that this run fails 39% of the
  time, so it stays; what goes is every other full run.
- `agents-tasks:verify-task` and the `spec-validator` agent are unchanged: they run once per task.
- Checks: `test_task_run.py` asserts that the implementer prompt and the fix-round prompt carry the
  touched-tests line and name no full-suite run.

#### Phase 2: Long commands stay out of subagents (A2)

- Files: `references/briefs.md`, `lib/task_run.py` (the same prompts),
  `plugins/agents-core/agents/implementer.md`. Ceiling: 15 changed lines.
- The rule: the harness moves a subagent's foreground command to the background after 180 seconds,
  and in 85% of the measured cases the subagent then got no completion notice and polled. So a
  subagent does not start a command it expects to run longer than two minutes (the margin under
  180 seconds): it names the command in its reply and the orchestrator runs it. A longer timeout in
  the brief does not help and is not written.
- `TaskStop` leaves the implementer's tool list; the profile shows it fails in subagents.
- Checks: `python3 scripts/build.py`; `test_task_run.py` asserts the line in both prompts.

#### Phase 3: Peer stamp keyed on the patch (B12)

Needs the owner's yes on one point before it starts: a branch rebased onto a changed base keeps its
stamp when its own diff is unchanged, so the reviewed diff, not the result on the new base, is what
was approved.

- Files: `plugins/agents-core/lib/peer.py`, `plugins/agents-core/hooks/block-dangerous-git.sh` (the
  push check and its comment), `plugins/agents-core/hooks/tests/test-hooks.sh`,
  `scripts/tests/test-at.sh`, `CHANGELOG.md`. Ceiling: 60 changed lines.
- What changes: the stamp name is one id over the whole branch diff,
  `git diff <merge-base(base, HEAD)> HEAD -- . ':(exclude)docs/tasks_manager/'` piped to
  `git patch-id --verbatim`, computed the same way in `peer.py` and in the hook. `--verbatim`,
  because the default ignores whitespace and an indentation change must lose the stamp. The base is
  the branch the push hook already protects. Old SHA stamps stay valid.
- Fact to confirm first: how the hook can name the base without a network call, for a branch with no
  upstream.
- Checks: a rebased, unchanged branch passes the push check; a squash passes; a merge of the base
  passes; a whitespace-only change does not; a content change does not; an old SHA stamp passes.

## Moved out

The permission preflight (B10) is not built here. The 72 denials the profile counted came from the
`auto` mode classifier, a model, which no reader of settings can predict. The part code can check
(the task's commands against the deny and ask lists and the repo's own hooks) belongs to
`at sup ready` in the supervisor plan.

## Order

Phases 1 and 2 together, then a release. Phase 3 after the owner's answer, in its own release.

## Acceptance

- The implementer and fix-round prompts, in the briefs and in `task_run.py`, name touched tests only
  and the two-minute rule; the suite asserts it.
- `execute-plan` names one full run per phase, by the orchestrator, before the commit.
- A reviewed branch survives a rebase without a second review, and loses the stamp on any change.
- Measured after two weeks of use with the profile's own scripts: full-suite runs per phase and
  subagent commands moved to the background, against the profile's numbers.

## Out of scope

- The cost of the review loop itself (the profile's conclusion 3).
- A limit on subagents per host.
