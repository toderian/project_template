# Phase 4, fix round 1: open findings

Sources: review-spec.md (S), review-quality.md (Q), review-security.md (X). Lane A = code, lane B = skill and docs.

## Lane A (code)

Required shape first: this round must end with fewer net lines in sup.py than it starts with (now +106/-8).
One parse of a task per pack check: `pack_problems` parses each task once and hands the parsed task to the
rules; `readiness` takes an already parsed task (keep its public behaviour for `at sup ready <ID>`). One parser
of the `Repos` cell: `sup_workers._task_repos` (delete `sup._slugs`). One place for the `task_brief` import
(`sw._task_meta`'s or `_brief`, not both). The slug of an entry comes from `ENTRY_RE`'s group through one helper
in task_lanes.py, not from three `partition(":")` calls.

1. [C] Q1, X5: `pack_problems` never raises: catch `ValueError` (covers `UnicodeDecodeError`) beside the others,
   and `at sup ready --pack <bad name>` prints one line and exits 2 or 3, no traceback. Test both.
2. [I] S1, Q2: a slug in a task's `Repos` row that is a row of the registry and is not the hub's own slug needs a
   pack branch, with or without a map line. Use the registry `sw._repos(hub)` returns. The map-only fallback
   applies only when the hub's own slug cannot be determined. Test: registry slug without a map line, pack
   without that branch: one problem line.
3. [I] Q3: `Repos` cell parsed by `sw._task_repos` only, so the shared-file rule and phase 1's serialising agree.
   Test: `Repos: \`sib\`; x` in two tasks that share `sib:x.py` in a parallel pack is flagged or serialised
   consistently with what `next_tasks` does.
4. [I] Q4: remove the setUp patch of `sup.task_lines` from test_sup_workers.py: the fixture writes minimal task
   files that pass `at sup ready` (one helper), or patch per test where a test is about something else and say
   why. Add one test that `start-pack` refuses with a per-task readiness line and leaves the pack state as it was.
5. [I] S2, Q5: the size, by the shape above.
6. [M] Q6: when `_edges` refuses, do not run the shared-file rule (its line would be false).
7. [M] Q7: an unreadable or malformed profile.json is its own line naming the file; a missing file stays "no
   resources known".
8. [M] Q8: a task whose file is in the archive directory counts as done for the pack check, as `_blockers`
   already counts it. Test: paused pack, one task archived by hand, `start-pack` restarts.
9. [M] S3: the phase test matches `Phase <number>` after a task id (`RM-281 Phase 1`, `RM-281 phase 2`), not the
   bare word anywhere in the cell. Test `TST-2 (after its phase-out)` passes.
10. [M] X1: a phase heading printed in a problem line goes through the cut-and-clean used elsewhere
    (`sup_state._clean` or the local `_cut`), so no control character and at most 60 characters reach the output.
11. [M] X2: a resource name that does not match `sup_state.RES` is shown as `!r` cut to 40 characters.
12. [M] X3: `entry_ok` refuses a `.` path segment (`src/./a.py`), as it refuses `..`.
13. [M] S6: one line per problem: a resource the profile lacks and that has no duration gives one line, not two.
    The order of lines is free; do not spend code on it.
Not in this round: X4 (quadratic check; ruled, a task with thousands of `Files:` entries is not a real input).

## Lane B (skill and docs)

14. [M] S4: README.md: the `agents-tasks` count must equal the number of `plugins/agents-tasks/skills/*/SKILL.md`
    (count them), and the README's per-plugin counts must sum to the 76 the tests assert.
15. [M] S5: prepare-pack SKILL.md names `agents-tasks:supervise` once, at the hand-off; wrap line 64.
16. [M] prepare-pack SKILL.md: the description says what the skill writes truthfully (task files, and the pack
    record through `at sup pack`); the `at sup ready --pack <name>` example says a profile is needed
    (`--profile <name>` or `AGENTS_SUPERVISOR`).
17. [M] todo-convention.md:204: `Files:` may be more than one line per phase; say "the `Files:` lines".
18. [M] After lane A's fix: a registry slug in `Repos` needs a pack branch even without a map line; a `.` path
    segment is refused; a blocker cell names a phase only as `<ID> Phase <n>`. Adjust any sentence that says otherwise.
