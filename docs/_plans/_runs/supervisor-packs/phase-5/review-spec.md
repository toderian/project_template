Stage: spec, phase 5. Checklist met except: the ignore check in effect (finding 1), refusal for anything in the way (partly, finding 2), the outside-worktree rule untested (finding 3).

## Status: DONE_WITH_CONCERNS
## Verdict: FAIL
## Findings: 6 (C:1 I:2 M:3)
1. [C] plugins/agents-core/lib/sup_state.py:171 — with `.gitignore` `shared/` and an existing `hub/shared/`, `git check-ignore shared` in the hub returns 0, the entry is accepted, the link in the task worktree is untracked (`?? shared`), `sup land` refuses with "uncommitted changes" and `git add -A` would commit the link. The usual setup. Fix direction: test the ignore status of the link itself in the task worktree after linking, and refuse naming the entry.
2. [I] plugins/agents-core/lib/sup_workers.py:818,826-827 — OSError from `mkdir`/`symlink_to` is not turned into Refused: a file at a parent of the link gives a traceback.
3. [I] plugins/agents-core/lib/sup_workers.py:824 — the "outside the worktree" refusal has no test.
4. [M] plugins/agents-tasks/skills/supervise/SKILL.md:50 — say plainly: write `lab-results`, not `lab-results/`, in `.gitignore`, because the worktree holds a link.
5. [M] scripts/tests/test_sup_tick.py:119 — the `.local/repos.map` case passes a string, proving "must be a list"; no case for backslash or control character; the new prompt sentence has no assertion.
6. [M] plugins/agents-core/lib/sup.py:281 — `sup land` without a profile moves the link itself to `kept/<ID>`; hub content intact.
