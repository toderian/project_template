Stage: spec, phase 4. Checklist: all items met except the code ceiling (107 against 80) and "every slug is a pack repo" (partly, finding 1).

## Status: DONE_WITH_CONCERNS
## Verdict: FAIL
## Findings: 6 (C:0 I:2 M:4)
1. [I] plugins/agents-core/lib/sup.py:437 — a `Repos` slug is checked only when `.local/repos.map` has a line for it; a registry slug without a map line passes `ready --pack` although `at sup pack` can never give it a branch. The registry (first value of `sw._repos(hub)`) is discarded. No test.
2. [I] phase-4/size.md — code net +107 against 80, no reason given.
3. [M] plugins/agents-core/lib/sup.py:433 — phase test is `re.search("phase", cell, re.I)` on the whole cell: `TST-2 (after its phase-out)` is refused.
4. [M] README.md:168 — says agents-tasks has 27 skills; the tree has 28 (the base was already one short).
5. [M] plugins/agents-tasks/skills/prepare-pack/SKILL.md:14 — `agents-tasks:supervise` named twice (line 14 and the hand-off at 77); line 64 is 181 characters.
6. [M] plugins/agents-core/lib/sup.py:416-437 — line order differs from the contract; a resource without a duration that the profile lacks gives two lines.

Imprecise text: todo-convention.md:204 "one `Files:` line" (fence reads every line); prepare-pack SKILL.md:60 shows
`at sup ready --pack <name>` without `--profile`; SKILL.md:3 "edits task files only" while step 6 runs `at sup pack`.
Test gap: no test drives `start-pack` to a per-task readiness line.
